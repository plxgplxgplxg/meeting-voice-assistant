import os
import uuid
import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.security import sanitize_filename


class StorageService:
    """Service handling local filesystem object storage for audio and export files."""

    def __init__(self, root_dir: str | None = None) -> None:
        self.root_dir = root_dir or settings.storage_root
        os.makedirs(self.root_dir, exist_ok=True)

    async def save_upload_file(
        self, meeting_id: uuid.UUID, file: UploadFile
    ) -> tuple[str, int]:
        """Save an uploaded file to the meeting storage directory.

        Args:
            meeting_id: Target meeting UUID.
            file: FastAPI UploadFile object.

        Returns:
            Tuple of relative/absolute storage path and file size in bytes.
        """
        clean_name = sanitize_filename(file.filename or f"audio_{uuid.uuid4().hex[:8]}.wav")
        meeting_dir = os.path.join(self.root_dir, str(meeting_id))
        os.makedirs(meeting_dir, exist_ok=True)

        target_path = os.path.join(meeting_dir, clean_name)
        total_bytes = 0

        async with aiofiles.open(target_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(chunk)
                total_bytes += len(chunk)

        return target_path, total_bytes

    async def save_bytes(
        self, meeting_id: uuid.UUID, file_name: str, data: bytes
    ) -> str:
        """Save binary data to a file in the meeting directory.

        Args:
            meeting_id: Target meeting UUID.
            file_name: Desired file name.
            data: Binary byte contents.

        Returns:
            Absolute target file path.
        """
        clean_name = sanitize_filename(file_name)
        meeting_dir = os.path.join(self.root_dir, str(meeting_id))
        os.makedirs(meeting_dir, exist_ok=True)

        target_path = os.path.join(meeting_dir, clean_name)
        async with aiofiles.open(target_path, "wb") as out_file:
            await out_file.write(data)

        return target_path

    def get_file_path(self, storage_path: str) -> str:
        """Resolve and verify existence of stored file."""
        return storage_path if os.path.exists(storage_path) else ""
