import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import ValidationFailedError

CHUNK_SIZE = 1024 * 1024


class StorageService:
    """Local filesystem object storage addressed by relative storage keys.

    Callers only ever see keys such as ``<meeting_id>/<audio_file_id>.wav``.
    Absolute paths are produced exclusively by :meth:`resolve`, which guarantees
    the result stays inside the storage root.
    """

    def __init__(self, root_dir: str | None = None, max_upload_mb: int | None = None) -> None:
        """Initialize storage.

        Args:
            root_dir: Storage root directory. Defaults to ``settings.storage_root``.
            max_upload_mb: Upload size limit. Defaults to ``settings.max_upload_mb``.
        """
        self.root = Path(root_dir or settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_upload_bytes = (max_upload_mb or settings.max_upload_mb) * 1024 * 1024

    def resolve(self, key: str) -> Path:
        """Translate a storage key into an absolute path inside the root.

        Args:
            key: Relative storage key.

        Returns:
            Absolute filesystem path.

        Raises:
            ValidationFailedError: If the key would escape the storage root.
        """
        candidate = (self.root / key).resolve()
        if candidate == self.root or self.root not in candidate.parents:
            raise ValidationFailedError("Invalid storage key.", code="INVALID_STORAGE_KEY")
        return candidate

    def exists(self, key: str) -> bool:
        """Return whether a stored file exists for the given key."""
        try:
            return self.resolve(key).is_file()
        except ValidationFailedError:
            return False

    async def save_upload(
        self, meeting_id: uuid.UUID, audio_file_id: uuid.UUID, extension: str, file: UploadFile
    ) -> tuple[str, int]:
        """Stream an upload to disk, enforcing the size limit.

        The file is named from generated identifiers so two uploads with the
        same original name never overwrite each other.

        Args:
            meeting_id: Owning meeting.
            audio_file_id: Identifier of the new audio file row.
            extension: Lower-case extension including the dot.
            file: Uploaded multipart file.

        Returns:
            Tuple of storage key and size in bytes.

        Raises:
            ValidationFailedError: With status 413 if the file exceeds the limit.
        """
        key = f"{meeting_id}/{audio_file_id}{extension}"
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        try:
            async with aiofiles.open(target, "wb") as out_file:
                while chunk := await file.read(CHUNK_SIZE):
                    total += len(chunk)
                    if total > self.max_upload_bytes:
                        raise ValidationFailedError(
                            f"File exceeds the {self.max_upload_bytes // (1024 * 1024)} MB upload limit.",
                            code="UPLOAD_TOO_LARGE",
                            status_code=413,
                        )
                    await out_file.write(chunk)
        except BaseException:
            self.delete(key)
            raise
        return key, total

    def read_head(self, key: str, size: int = 64) -> bytes:
        """Read the first bytes of a stored file for content sniffing."""
        with open(self.resolve(key), "rb") as handle:
            return handle.read(size)

    def delete(self, key: str) -> None:
        """Delete a stored file, ignoring missing files."""
        try:
            os.remove(self.resolve(key))
        except (FileNotFoundError, ValidationFailedError):
            pass
