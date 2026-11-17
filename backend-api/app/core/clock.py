from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime.

    Timestamps are stored as naive UTC until the timezone-aware migration
    (roadmap T4.1) lands, so every caller shares one source of "now".

    Returns:
        Naive datetime representing the current UTC instant.
    """
    return datetime.now(UTC).replace(tzinfo=None)
