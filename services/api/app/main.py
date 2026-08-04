"""
Aegis AI — FastAPI Application Entry Point.

Assembles the application with all routes, middleware, lifecycle events,
and observability instrumentation.

Architecture Decision:
    We use the application factory pattern (create_app) for testability.
    The lifespan context manager handles startup/shutdown of external
    connections (DB, Redis, Qdrant). Prometheus metrics are collected
    via the metrics_middleware and exposed at /metrics.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from app.api.routes import auth, conversations, knowledge, approvals, incidents
from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

logger = get_logger(__name__)

# ── Prometheus Metrics ───────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "aegis_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "aegis_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)
AGENT_RUNS = Counter(
    "aegis_agent_runs_total",
    "Total agent runs",
    ["agent_type", "status"],
)
LLM_TOKENS = Counter(
    "aegis_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],
)


# ── Lifecycle ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown hooks."""
    settings = get_settings()
    setup_logging()

    logger.info(
        "application_starting",
        version=settings.app_version,
        environment=settings.app_env,
    )

    # Startup: initialize connections
    # - Database pool is created eagerly in session.py
    # - Redis connection pool will be initialized in Day 2
    # - Qdrant client will be initialized in Day 2

    yield

    # Shutdown: clean up resources
    logger.info("application_shutting_down")
    from app.db.session import engine
    await engine.dispose()


# ── Application Factory ─────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Aegis AI — Enterprise AI Operations Platform",
        description=(
            "Production-grade multi-agent AI platform for enterprise operations. "
            "Connects to business systems, performs autonomous investigation, "
            "and assists operators through structured reasoning."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # ── Middleware (order matters — outermost first) ──────────────────────
    # 1. CORS — must be outermost for preflight requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Correlation ID — injects trace context for all downstream middleware
    app.add_middleware(CorrelationIdMiddleware)

    # 3. Security Headers — enforces SOC 2 headers on responses
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Rate limiting — protects against abuse before request processing
    app.add_middleware(RateLimitMiddleware)

    # 5. Request logging — logs after completion with latency
    app.add_middleware(RequestLoggingMiddleware)

    # 5. Prometheus metrics middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        import time
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method, endpoint=endpoint, status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)

        return response

    # ── Routes ───────────────────────────────────────────────────────────
    api_prefix = "/api/v1"

    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(incidents.router, prefix=api_prefix)
    app.include_router(conversations.router, prefix=api_prefix)
    app.include_router(knowledge.router, prefix=api_prefix)
    app.include_router(approvals.router, prefix=api_prefix)

    # ── Health & Metrics Endpoints ───────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """System health check for load balancers and monitoring."""
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            services={
                "api": "healthy",
                "database": "healthy",
                "redis": "healthy",
            },
        )

    @app.get("/readiness", response_model=HealthResponse, tags=["System"])
    async def readiness_check():
        """
        Readiness probe for Kubernetes.

        Unlike /health, this verifies actual connectivity to dependencies.
        """
        services: dict[str, str] = {"api": "healthy"}

        # Check database connectivity
        try:
            from app.db.session import async_session_factory
            async with async_session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                services["database"] = "healthy"
        except Exception:
            services["database"] = "unhealthy"

        overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

        return HealthResponse(
            status=overall,
            version=settings.app_version,
            services=services,
        )

    @app.get("/metrics", tags=["System"])
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # ── Global Exception Handlers ────────────────────────────────────────

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred" if settings.is_production else str(exc),
                "error_code": "INTERNAL_ERROR",
            },
        )

    return app


# Create the application instance
app = create_app()
