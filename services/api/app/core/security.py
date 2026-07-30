"""
Aegis AI — Security Module.

Handles JWT token creation/validation, password hashing, and authentication
dependencies for FastAPI route protection.

Security Architecture:
    - Access tokens: Short-lived JWTs (30 min default) for API authentication
    - Refresh tokens: Long-lived JWTs (7 days) stored in HTTP-only cookies
    - Password hashing: bcrypt with automatic salt generation
    - RBAC: Role-based access control with hierarchical permissions
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.enums import Permission, Role, ROLE_PERMISSIONS

logger = get_logger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


# ── Token Models ─────────────────────────────────────────────────────────────


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""
    sub: str  # user ID
    org_id: str
    role: str
    permissions: list[str]
    exp: datetime
    iat: datetime
    jti: str  # unique token ID for revocation
    token_type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access + refresh token pair returned on authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry


# ── Password Utilities ───────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Operations ─────────────────────────────────────────────────────


def create_access_token(
    user_id: str,
    org_id: str,
    role: Role,
    settings: Settings | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: The authenticated user's ID.
        org_id: The user's organization ID.
        role: The user's RBAC role.
        settings: Application settings (injected for testing).

    Returns:
        Encoded JWT access token string.
    """
    if settings is None:
        settings = get_settings()

    permissions = [p.value for p in ROLE_PERMISSIONS.get(role, set())]
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role.value,
        "permissions": permissions,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "access",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    org_id: str,
    role: Role,
    settings: Settings | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    if settings is None:
        settings = get_settings()

    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role.value,
        "permissions": [],
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "token_type": "refresh",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(user_id: str, org_id: str, role: Role) -> TokenPair:
    """Generate both access and refresh tokens."""
    settings = get_settings()
    return TokenPair(
        access_token=create_access_token(user_id, org_id, role, settings),
        refresh_token=create_refresh_token(user_id, org_id, role, settings),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


def decode_token(token: str, settings: Settings | None = None) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException: If the token is invalid, expired, or malformed.
    """
    if settings is None:
        settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── FastAPI Dependencies ─────────────────────────────────────────────────────


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ] = None,
) -> TokenPayload:
    """
    FastAPI dependency that extracts and validates the current user
    from the Authorization header.

    Usage:
        @router.get("/protected")
        async def protected(user: TokenPayload = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_token(credentials.credentials)


def require_permission(permission: Permission):
    """
    Factory for FastAPI dependencies that enforce specific permissions.

    Usage:
        @router.post("/agents/execute")
        async def execute_agent(
            user: TokenPayload = Depends(require_permission(Permission.AGENT_EXECUTE))
        ):
            ...
    """

    async def _check_permission(
        user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if permission.value not in user.permissions:
            logger.warning(
                "permission_denied",
                user_id=user.sub,
                required=permission.value,
                role=user.role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required",
            )
        return user

    return _check_permission


def require_role(minimum_role: Role):
    """
    Factory for FastAPI dependencies that enforce minimum role level.

    Role hierarchy: SUPER_ADMIN > ORG_ADMIN > TEAM_LEAD > OPERATOR > VIEWER
    """
    role_hierarchy = [
        Role.VIEWER, Role.OPERATOR, Role.TEAM_LEAD, Role.ORG_ADMIN, Role.SUPER_ADMIN,
    ]

    async def _check_role(
        user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        try:
            user_level = role_hierarchy.index(Role(user.role))
            required_level = role_hierarchy.index(minimum_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid role",
            )

        if user_level < required_level:
            logger.warning(
                "role_insufficient",
                user_id=user.sub,
                user_role=user.role,
                required_role=minimum_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{minimum_role.value}' or higher required",
            )
        return user

    return _check_role
