"""
Unit tests for SecurityHeadersMiddleware and Tracing.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import SecurityHeadersMiddleware
from app.core.tracing import TracerManager


def test_security_headers_middleware_injects_headers():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def test_route():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in response.headers


def test_tracer_manager_initialization_graceful():
    manager = TracerManager()
    assert manager.enabled is False
    manager.initialize()  # Should handle missing OTLP endpoint gracefully without crashing
    assert manager.enabled is False


@pytest.mark.asyncio
async def test_tracer_decorator_runs_function():
    manager = TracerManager()

    @manager.trace_span("test_span")
    async def sample_func(a: int, b: int) -> int:
        return a + b

    result = await sample_func(2, 3)
    assert result == 5
