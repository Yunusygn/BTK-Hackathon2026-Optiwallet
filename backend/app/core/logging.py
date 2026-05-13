"""
Structured Logging Configuration.

Structlog kullanarak production-ready JSON logging.
Her log satırı yapılandırılmış (request_id, user_id, vs. eklenebilir).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    - Development: human-readable console output
    - Production: JSON formatted logs (for log aggregators)
    """

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Standard logging config
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Common processors (her log için çalışır)
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_app_context,
    ]

    if settings.LOG_FORMAT == "json":
        # Production: JSON output
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: pretty console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_app_context(
    logger: Any,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Add application context to every log entry.

    Adds: app name, environment, version.
    """
    event_dict["app"] = settings.APP_NAME
    event_dict["env"] = settings.APP_ENV
    return event_dict


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.

    Args:
        name: Optional logger name (genelde __name__ kullanılır).

    Returns:
        BoundLogger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_created", user_id="123", email="test@example.com")
    """
    return structlog.get_logger(name) if name else structlog.get_logger()