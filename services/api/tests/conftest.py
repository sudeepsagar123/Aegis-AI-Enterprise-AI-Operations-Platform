"""
Aegis AI — Test Configuration and Fixtures.

Provides shared fixtures for all test modules:
    - Test settings with deterministic secret keys
    - Async database sessions with test database
    - Test user and organization factories
    - FastAPI test client
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.core.security import create_access_token
from app.domain.enums import Role


@pytest.fixture
def test_settings() -> Settings:
    """Deterministic settings for unit tests — no .env file needed."""
    return Settings(
        app_env="development",
        app_debug=True,
        app_version="0.1.0-test",
        jwt_secret_key="test-secret-key-for-unit-tests-only-do-not-use-in-production",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=30,
        jwt_refresh_token_expire_days=7,
        database_host="localhost",
        database_name="aegis_ai_test",
        database_user="aegis",
        database_password="test",
        redis_host="localhost",
    )


@pytest.fixture
def test_user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def test_org_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def operator_token(test_settings, test_user_id, test_org_id) -> str:
    """Generate a valid access token for an OPERATOR role user."""
    return create_access_token(
        test_user_id, test_org_id, Role.OPERATOR, test_settings,
    )


@pytest.fixture
def admin_token(test_settings, test_user_id, test_org_id) -> str:
    """Generate a valid access token for an ORG_ADMIN role user."""
    return create_access_token(
        test_user_id, test_org_id, Role.ORG_ADMIN, test_settings,
    )


@pytest.fixture
def viewer_token(test_settings, test_user_id, test_org_id) -> str:
    """Generate a valid access token for a VIEWER role user."""
    return create_access_token(
        test_user_id, test_org_id, Role.VIEWER, test_settings,
    )
