def format_timestamp(seconds: float, separator: str = ":", ms_separator: str = ",") -> str:
    """Format seconds into HH:MM:SS,mmm or HH:MM:SS.mmm format.

    Args:
        seconds: Float seconds.
        separator: Time unit delimiter (default ':').
        ms_separator: Milliseconds delimiter (default ',').

    Returns:
        Formatted timestamp string.
    """
    total_ms = max(0, round(seconds * 1000))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{hours:02d}{separator}{minutes:02d}{separator}{secs:02d}{ms_separator}{ms:03d}"
