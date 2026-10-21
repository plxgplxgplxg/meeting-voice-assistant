from typing import Optional


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal attacks.

    Args:
        filename: Original file name string.

    Returns:
        Sanitized file name string.
    """
    return filename.replace("/", "").replace("\\", "").strip()
