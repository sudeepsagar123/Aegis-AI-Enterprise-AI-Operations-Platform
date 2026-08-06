"""
Aegis AI — Middleware Stack.

Production-grade middleware for:
    - Correlation ID propagation (distributed tracing)
    - Rate limiting (token bucket per IP)
    - Request/response logging
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Correlation ID Middleware ────────────────────────────────────────────────


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation ID into every request for distributed tracing.

    If the client sends an X-Correlation-ID header, it is propagated.
    Otherwise, a new UUID is generated. The ID is included in all
    log entries and returned in the response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )

        # Store in request state for downstream access
        request.state.correlation_id = correlation_id

        # Inject into structlog context
        import structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


# ── Rate Limiting Middleware ─────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter per client IP.

    Design Decision:
        We use an in-memory token bucket for simplicity in development.
        In production with horizontal scaling, this should be replaced
        with Redis-based rate limiting (e.g., using a Lua script for
        atomic token bucket operations).

    Configuration:
        rate_limit_requests_per_minute: Sustained request rate
        rate_limit_burst: Maximum burst size above the sustained rate
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        settings = get_settings()
        self.rate = settings.rate_limit_requests_per_minute / 60.0  # tokens per second
        self.burst = settings.rate_limit_burst
        self.buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tokens": self.burst, "last_refill": time.monotonic()}
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a reverse proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _consume_token(self, client_ip: str) -> bool:
        """Attempt to consume a token from the bucket. Returns True if allowed."""
        bucket = self.buckets[client_ip]
        now = time.monotonic()
        elapsed = now - bucket["last_refill"]

        # Refill tokens based on elapsed time
        bucket["tokens"] = min(
            self.burst, bucket["tokens"] + elapsed * self.rate
        )
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for health checks, metrics, and local development mode
        settings = get_settings()
        if settings.app_env == "development" or request.url.path in ("/health", "/metrics", "/readiness"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if not self._consume_token(client_ip):
            logger.warning("rate_limit_exceeded", client_ip=client_ip, path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please retry after a short delay.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# ── Request Logging Middleware ───────────────────────────────────────────────


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with method, path, status code, and latency.
    Excludes noisy endpoints (health, metrics) from info-level logging.
    """

    QUIET_PATHS = {"/health", "/metrics", "/readiness", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        path = request.url.path

        if path not in self.QUIET_PATHS:
            logger.info(
                "http_request",
                method=request.method,
                path=path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=request.client.host if request.client else "unknown",
            )

        response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
        return response


# ── Security Headers Middleware ─────────────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enforces enterprise security headers on all HTTP responses for SOC 2 compliance.

    Headers set:
        - X-Frame-Options: DENY (Prevents clickjacking)
        - X-Content-Type-Options: nosniff (Prevents MIME sniffing)
        - X-XSS-Protection: 1; mode=block (Legacy XSS protection)
        - Strict-Transport-Security: max-age=31536000; includeSubDomains (Enforces HSTS)
        - Referrer-Policy: strict-origin-when-cross-origin
        - Permissions-Policy: camera=(), microphone=(), geolocation=()
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

