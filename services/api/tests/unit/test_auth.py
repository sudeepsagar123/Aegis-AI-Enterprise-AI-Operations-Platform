"""
Aegis AI — Unit Tests for Authentication and Security.

Tests JWT token creation/validation, password hashing, RBAC,
and permission enforcement without any database dependency.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.enums import Permission, Role, ROLE_PERMISSIONS


# ── Password Hashing ────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_and_verify_password(self):
        password = "SecureP@ssw0rd!123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt generates a unique salt each time."""
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2

    def test_empty_password_hashes(self):
        """Empty passwords should still hash (validation is at API layer)."""
        hashed = hash_password("")
        assert verify_password("", hashed)


# ── JWT Tokens ───────────────────────────────────────────────────────────────


class TestJWTTokens:
    @pytest.fixture
    def settings(self):
        return Settings(
            jwt_secret_key="test-secret-key-for-unit-tests-only",
            jwt_algorithm="HS256",
            jwt_access_token_expire_minutes=30,
            jwt_refresh_token_expire_days=7,
        )

    def test_create_access_token(self, settings):
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        token = create_access_token(user_id, org_id, Role.OPERATOR, settings)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self, settings):
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        token = create_access_token(user_id, org_id, Role.OPERATOR, settings)
        payload = decode_token(token, settings)

        assert payload.sub == user_id
        assert payload.org_id == org_id
        assert payload.role == Role.OPERATOR.value
        assert payload.token_type == "access"

    def test_access_token_contains_permissions(self, settings):
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        token = create_access_token(user_id, org_id, Role.OPERATOR, settings)
        payload = decode_token(token, settings)

        expected_perms = {p.value for p in ROLE_PERMISSIONS[Role.OPERATOR]}
        actual_perms = set(payload.permissions)
        assert actual_perms == expected_perms

    def test_create_token_pair(self, settings):
        import app.core.security as sec_module
        original = sec_module.get_settings
        sec_module.get_settings = lambda: settings

        try:
            pair = create_token_pair(str(uuid.uuid4()), str(uuid.uuid4()), Role.OPERATOR)
            assert pair.access_token
            assert pair.refresh_token
            assert pair.token_type == "bearer"
            assert pair.expires_in == 30 * 60
        finally:
            sec_module.get_settings = original

    def test_refresh_token_type(self, settings):
        token = create_refresh_token(str(uuid.uuid4()), str(uuid.uuid4()), Role.VIEWER, settings)
        payload = decode_token(token, settings)
        assert payload.token_type == "refresh"

    def test_refresh_token_has_no_permissions(self, settings):
        """Refresh tokens must not carry permissions — only access tokens do."""
        token = create_refresh_token(str(uuid.uuid4()), str(uuid.uuid4()), Role.ORG_ADMIN, settings)
        payload = decode_token(token, settings)
        assert payload.permissions == []

    def test_decode_invalid_token_raises(self, settings):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.string", settings)
        assert exc_info.value.status_code == 401

    def test_decode_wrong_secret_raises(self, settings):
        token = create_access_token(str(uuid.uuid4()), str(uuid.uuid4()), Role.VIEWER, settings)
        wrong_settings = Settings(
            jwt_secret_key="wrong-secret-key",
            jwt_algorithm="HS256",
        )
        with pytest.raises(HTTPException):
            decode_token(token, wrong_settings)

    def test_token_jti_is_unique(self, settings):
        """Each token must have a unique JTI for revocation support."""
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        token1 = create_access_token(user_id, org_id, Role.OPERATOR, settings)
        token2 = create_access_token(user_id, org_id, Role.OPERATOR, settings)

        payload1 = decode_token(token1, settings)
        payload2 = decode_token(token2, settings)

        assert payload1.jti != payload2.jti


# ── RBAC ─────────────────────────────────────────────────────────────────────


class TestRBAC:
    def test_super_admin_has_all_permissions(self):
        perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        assert len(perms) == len(Permission)

    def test_viewer_has_limited_permissions(self):
        perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.CONVERSATION_READ in perms
        assert Permission.INCIDENT_READ in perms
        assert Permission.AGENT_EXECUTE not in perms
        assert Permission.ADMIN_USERS not in perms

    def test_operator_cannot_administer(self):
        perms = ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.ADMIN_USERS not in perms
        assert Permission.ADMIN_SETTINGS not in perms

    def test_operator_can_manage_incidents(self):
        perms = ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.INCIDENT_CREATE in perms
        assert Permission.INCIDENT_READ in perms
        assert Permission.INCIDENT_UPDATE in perms

    def test_viewer_cannot_create_incidents(self):
        perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.INCIDENT_CREATE not in perms

    def test_role_hierarchy(self):
        """Higher roles should have more permissions than lower roles."""
        viewer_count = len(ROLE_PERMISSIONS[Role.VIEWER])
        operator_count = len(ROLE_PERMISSIONS[Role.OPERATOR])
        lead_count = len(ROLE_PERMISSIONS[Role.TEAM_LEAD])
        admin_count = len(ROLE_PERMISSIONS[Role.ORG_ADMIN])
        super_count = len(ROLE_PERMISSIONS[Role.SUPER_ADMIN])

        assert viewer_count < operator_count
        assert operator_count < lead_count
        assert lead_count <= admin_count
        assert admin_count <= super_count

    def test_service_account_permissions(self):
        perms = ROLE_PERMISSIONS[Role.SERVICE_ACCOUNT]
        assert Permission.AGENT_EXECUTE in perms
        assert Permission.INCIDENT_CREATE in perms
        assert Permission.ADMIN_USERS not in perms


# ── Domain Enums ─────────────────────────────────────────────────────────────


class TestDomainEnums:
    def test_incident_severity_values(self):
        from app.domain.enums import IncidentSeverity
        assert IncidentSeverity.CRITICAL == "critical"
        assert IncidentSeverity.LOW == "low"

    def test_incident_status_values(self):
        from app.domain.enums import IncidentStatus
        assert IncidentStatus.OPEN == "open"
        assert IncidentStatus.RESOLVED == "resolved"
        assert IncidentStatus.CLOSED == "closed"

    def test_agent_type_values(self):
        from app.domain.enums import AgentType
        assert AgentType.COORDINATOR == "coordinator"
        assert AgentType.INCIDENT == "incident"
        assert AgentType.ROOT_CAUSE == "root_cause"

    def test_audit_action_values(self):
        from app.domain.enums import AuditAction
        assert AuditAction.USER_LOGIN == "user.login"
        assert AuditAction.INCIDENT_CREATE == "incident.create"
