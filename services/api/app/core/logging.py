"""
Aegis AI — Structured Logging.

Provides structured JSON logging via structlog, integrated with OpenTelemetry
trace context for distributed tracing correlation.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("processing_request", user_id=user.id, action="query")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace

from app.core.config import get_settings


def _add_trace_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject OpenTelemetry trace and span IDs into log records."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def _add_service_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add service metadata to every log entry."""
    settings = get_settings()
    event_dict["service"] = settings.app_name
    event_dict["environment"] = settings.app_env
    event_dict["version"] = settings.app_version
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog for structured JSON logging in production
    and human-readable console output in development.
    """
    settings = get_settings()

    # Choose renderer based on environment
    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            _add_trace_context,
            _add_service_context,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure root Python logger
    log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence noisy third-party loggers
    for logger_name in ("uvicorn.access", "httpx", "httpcore", "aiokafka"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance bound to the given module name.

    Args:
        name: Module name, typically __name__.

    Returns:
        A structlog BoundLogger with trace context and service metadata.
    """
    return structlog.get_logger(name)
