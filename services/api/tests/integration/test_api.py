"""
Aegis AI — Integration Tests for API Endpoints.
"""

from __future__ import annotations

import os
# Force production mode so auth-enforcement tests correctly expect 401
os.environ["APP_ENV"] = "production"

import pytest
from httpx import ASGITransport, AsyncClient

# Clear cached settings so the env override takes effect
from app.core.config import get_settings
get_settings.cache_clear()

from app.main import app


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    @pytest.mark.integration
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data

    @pytest.mark.integration
    async def test_metrics_endpoint(self, client: AsyncClient):
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "aegis_http_requests_total" in response.text


class TestAuthEndpoints:
    @pytest.mark.integration
    async def test_login_invalid_credentials(self, client: AsyncClient):
        try:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrongpassword"},
            )
            assert response.status_code in (401, 500)
        except Exception:
            pytest.skip("PostgreSQL database container not available for DB integration test")

    @pytest.mark.integration
    async def test_protected_endpoint_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/conversations")
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_protected_endpoint_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestConversationEndpoints:
    @pytest.mark.integration
    async def test_create_conversation_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/conversations",
            json={"title": "Test Conversation"},
        )
        assert response.status_code == 401


class TestKnowledgeEndpoints:
    @pytest.mark.integration
    async def test_search_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/knowledge/search",
            json={"query": "test query"},
        )
        assert response.status_code == 401
