from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        Aware datetime in UTC, the single source of "now" for the backend.
    """
    return datetime.now(UTC)
