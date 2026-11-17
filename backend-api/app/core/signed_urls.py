import hashlib
import hmac
import uuid
from datetime import timedelta

from app.core.clock import utc_now
from app.core.config import settings

STREAM_URL_TTL = timedelta(minutes=10)


def _digest(meeting_id: uuid.UUID, expires_at: int) -> str:
    message = f"audio-stream:{meeting_id}:{expires_at}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def sign_audio_stream(meeting_id: uuid.UUID, ttl: timedelta = STREAM_URL_TTL) -> tuple[int, str]:
    """Create expiry and signature query values for a meeting's audio stream.

    The browser ``<audio>`` element cannot send a Bearer header, so the stream
    endpoint also accepts a short-lived HMAC signature issued to callers who
    already passed the VIEW check.

    Args:
        meeting_id: Meeting whose recording may be streamed.
        ttl: How long the signature stays valid.

    Returns:
        Tuple of the unix expiry timestamp and the hex signature.
    """
    expires_at = int((utc_now() + ttl).timestamp())
    return expires_at, _digest(meeting_id, expires_at)


def verify_audio_stream(meeting_id: uuid.UUID, expires_at: int, signature: str) -> bool:
    """Check a stream signature in constant time and reject expired ones.

    Args:
        meeting_id: Meeting being streamed.
        expires_at: Unix expiry timestamp from the URL.
        signature: Hex signature from the URL.

    Returns:
        True if the signature matches this meeting and has not expired.
    """
    if expires_at < int(utc_now().timestamp()):
        return False
    return hmac.compare_digest(signature, _digest(meeting_id, expires_at))
