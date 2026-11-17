import logging
import sys
from typing import TextIO

import structlog


def configure_logging(json_logs: bool, stream: TextIO | None = None) -> None:
    """Configure structlog for the process.

    Every log line carries the context variables bound by the request middleware
    (``request_id``) and the auth dependency (``user_id``). Production emits one JSON
    object per line, development emits a readable console format.

    Args:
        json_logs: Emit JSON when True, console format otherwise.
        stream: Output stream, defaults to stdout.
    """
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(stream or sys.stdout),
        cache_logger_on_first_use=False,
    )
