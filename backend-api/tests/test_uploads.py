import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.signed_urls import sign_audio_stream
from app.models.audio_file import AudioFileModel
from app.services.billing.quota_service import QuotaService
from app.services.storage_service import StorageService
from tests.conftest import MakeMeeting, RecordingDispatcher, RegisterUser

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64


def upload(client: AsyncClient, headers: dict[str, str], data: bytes = WAV, name: str = "standup.wav"):
    return client.post(
        "/api/v1/audio/upload",
        headers=headers,
        files={"file": (name, data, "audio/wav")},
    )


@pytest.mark.asyncio
async def test_anonymous_upload_is_rejected(client: AsyncClient) -> None:
    """Uploading without an account returns 401."""
    response = await upload(client, {})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_upload_creates_owned_meeting_in_uploaded_state(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession, storage: StorageService
) -> None:
    """A valid upload creates a meeting for the caller and a storage key built from ids."""
    user = await register_user("u@example.com")
    response = await upload(client, user.headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "uploaded"

    audio = await db_session.scalar(select(AudioFileModel))
    assert audio.storage_key == f"{body['meeting_id']}/{audio.id}.wav"
    assert storage.exists(audio.storage_key)
    assert audio.file_name == "standup.wav"


@pytest.mark.asyncio
async def test_same_filename_twice_never_overwrites(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting,
    db_session: AsyncSession, storage: StorageService,
) -> None:
    """Two uploads with an identical name produce two distinct stored files."""
    user = await register_user("u@example.com")
    meeting = await make_meeting(user.id, status="draft")
    url = f"/api/v1/meetings/{meeting.id}/audio"

    first = await client.post(url, headers=user.headers, files={"file": ("a.wav", WAV + b"1", "audio/wav")})
    assert first.status_code == 201, first.text
    meeting.status = "ready"
    await db_session.flush()
    second = await client.post(url, headers=user.headers, files={"file": ("a.wav", WAV + b"2", "audio/wav")})
    assert second.status_code == 201, second.text

    keys = [a.storage_key for a in (await db_session.scalars(select(AudioFileModel))).all()]
    assert len(set(keys)) == 2 and all(storage.exists(k) for k in keys)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "data", "code"),
    [
        ("notes.txt", WAV, "UNSUPPORTED_AUDIO_TYPE"),
        ("fake.wav", b"MZ\x90\x00 definitely not audio at all", "INVALID_AUDIO_CONTENT"),
    ],
)
async def test_invalid_uploads_are_rejected_and_leave_no_file(
    client: AsyncClient, register_user: RegisterUser, storage: StorageService,
    name: str, data: bytes, code: str,
) -> None:
    """Bad extensions and renamed non-audio files are refused and cleaned up."""
    user = await register_user("u@example.com")
    response = await upload(client, user.headers, data=data, name=name)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code
    assert not any(storage.root.rglob("*.*"))


@pytest.mark.asyncio
async def test_oversized_upload_returns_413_and_deletes_partial_file(
    client: AsyncClient, register_user: RegisterUser, storage: StorageService
) -> None:
    """The size limit is enforced while streaming and the partial file is removed."""
    user = await register_user("u@example.com")
    too_big = WAV + b"\x00" * (storage.max_upload_bytes + 1)
    response = await upload(client, user.headers, data=too_big)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"
    assert not any(p.is_file() for p in storage.root.rglob("*"))


@pytest.mark.asyncio
async def test_upload_is_blocked_when_quota_is_exhausted(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession, storage: StorageService
) -> None:
    """With no minutes left the upload returns 402 before any file is stored."""
    user = await register_user("u@example.com")
    await QuotaService(db_session).record_usage(user.id, None, 61 * 60)

    response = await upload(client, user.headers)
    assert response.status_code == 402
    assert response.json()["error"]["code"] == "QUOTA_EXCEEDED"
    assert not any(p.is_file() for p in storage.root.rglob("*"))


@pytest.mark.asyncio
async def test_processing_is_dispatched_only_after_commit(
    client: AsyncClient, register_user: RegisterUser, db_session: AsyncSession,
    dispatcher: RecordingDispatcher,
) -> None:
    """The worker is never enqueued before the request transaction commits."""
    user = await register_user("u@example.com")
    response = await upload(client, user.headers)
    assert response.status_code == 201
    assert dispatcher.calls == []

    await db_session.commit()
    assert len(dispatcher.calls) == 1
    assert str(dispatcher.calls[0][0]) == response.json()["meeting_id"]


@pytest.mark.asyncio
async def test_cannot_upload_into_meeting_without_edit_access(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """Uploading into someone else's meeting is forbidden."""
    owner = await register_user("owner@example.com")
    intruder = await register_user("intruder@example.com")
    meeting = await make_meeting(owner.id, status="draft")
    response = await client.post(
        f"/api/v1/meetings/{meeting.id}/audio",
        headers=intruder.headers,
        files={"file": ("a.wav", WAV, "audio/wav")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_into_meeting_being_processed_conflicts(
    client: AsyncClient, register_user: RegisterUser, make_meeting: MakeMeeting
) -> None:
    """A meeting that is transcribing cannot receive another recording."""
    user = await register_user("u@example.com")
    meeting = await make_meeting(user.id, status="transcribing")
    response = await client.post(
        f"/api/v1/meetings/{meeting.id}/audio",
        headers=user.headers,
        files={"file": ("a.wav", WAV, "audio/wav")},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_MEETING_STATE"


def test_storage_resolve_rejects_path_traversal(storage: StorageService) -> None:
    """Keys that escape the storage root are refused."""
    from app.core.errors import ValidationFailedError

    for key in ("../outside.wav", "a/../../outside.wav", "/etc/passwd", ""):
        with pytest.raises(ValidationFailedError):
            storage.resolve(key)
    assert storage.resolve("meeting/file.wav").is_relative_to(storage.root)


@pytest.mark.asyncio
async def test_signed_stream_url_allows_playback_without_a_bearer_token(
    client: AsyncClient, register_user: RegisterUser
) -> None:
    """The audio element can stream through a signed URL; tampered or expired ones are refused."""
    user = await register_user("u@example.com")
    uploaded = await upload(client, user.headers)
    meeting_id = uploaded.json()["meeting_id"]
    stream_path = f"/api/v1/meetings/{meeting_id}/audio/stream"

    issued = await client.get(f"{stream_path}-url", headers=user.headers)
    assert issued.status_code == 200, issued.text
    anonymous_play = await client.get(issued.json()["url"])
    assert anonymous_play.status_code == 200
    assert anonymous_play.content.startswith(b"RIFF")

    exp, sig = sign_audio_stream(uuid.UUID(meeting_id))
    assert (await client.get(f"{stream_path}?exp={exp}&sig=bad")).status_code == 403

    expired_exp, expired_sig = sign_audio_stream(uuid.UUID(meeting_id), ttl=timedelta(seconds=-5))
    assert (await client.get(f"{stream_path}?exp={expired_exp}&sig={expired_sig}")).status_code == 403

    other_meeting = f"/api/v1/meetings/{uuid.uuid4()}/audio/stream?exp={exp}&sig={sig}"
    assert (await client.get(other_meeting)).status_code in (403, 404)
