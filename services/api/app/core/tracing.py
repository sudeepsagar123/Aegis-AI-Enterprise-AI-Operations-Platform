"""
Aegis AI — OpenTelemetry Distributed Tracing Module.

Sets up OpenTelemetry tracing with OTLP exporter for Jaeger/Grafana Tempo integration.
Provides trace span decorators and context propagation helpers.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar
from collections.abc import Coroutine

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


class TracerManager:
    """
    Manages OpenTelemetry tracing lifecycle and span generation.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._tracer = None

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracer provider if configured."""
        settings = get_settings()
        if not settings.otel_exporter_otlp_endpoint:
            logger.info("tracing_disabled", reason="OTLP endpoint not configured")
            return

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": settings.app_name, "environment": settings.app_env})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            self._tracer = trace.get_tracer("aegis.ai")
            self.enabled = True
            logger.info("tracing_initialized", endpoint=settings.otel_exporter_otlp_endpoint)
        except Exception as e:
            logger.warning("tracing_init_failed", error=str(e))
            self.enabled = False

    def trace_span(self, name: str) -> Callable[[F], F]:
        """Decorator to trace an async function call."""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not self.enabled or self._tracer is None:
                    return await func(*args, **kwargs)

                with self._tracer.start_as_current_span(name) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("status", "ok")
                        return result
                    except Exception as exc:
                        span.set_attribute("status", "error")
                        span.record_exception(exc)
                        raise

            return wrapper  # type: ignore[return-value]
        return decorator


# Global tracer instance
tracer_manager = TracerManager()
