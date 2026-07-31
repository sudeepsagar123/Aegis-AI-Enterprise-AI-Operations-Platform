"""
Aegis AI — Authentication Routes.

Handles user registration, login, token refresh, and profile management.
Every auth event is recorded in the audit log for SOC 2 compliance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.schemas import (
    LoginRequest, RefreshTokenRequest, RegisterRequest,
    TokenResponse, UserResponse, UserUpdateRequest,
)
from app.core.logging import get_logger
from app.core.security import (
    TokenPayload, create_token_pair, decode_token,
    get_current_user, hash_password, verify_password,
)
from app.db.repositories.domain import OrganizationRepository, UserRepository
from app.db.session import DbSession
from app.domain.enums import AuditAction, Role
from app.services.audit import AuditService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request_body: RegisterRequest, request: Request, db: DbSession):
    """
    Register a new user and organization.

    Creates the organization, then the user as an org_admin.
    Returns access and refresh tokens.
    """
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    # Check if email already exists
    existing = await user_repo.get_by_email(request_body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create organization
    slug = request_body.org_name.lower().replace(" ", "-")[:100]
    org = await org_repo.create(name=request_body.org_name, slug=f"{slug}-{uuid.uuid4().hex[:6]}")

    # Create user
    user = await user_repo.create(
        org_id=org.id,
        email=request_body.email,
        hashed_password=hash_password(request_body.password[:72]),
        full_name=request_body.full_name,
        role=Role.ORG_ADMIN.value,
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.USER_REGISTER,
        org_id=org.id,
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": request_body.email, "org_name": request_body.org_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    logger.info("user_registered", user_id=str(user.id), org_id=str(org.id))

    token_pair = create_token_pair(str(user.id), str(org.id), Role.ORG_ADMIN)
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request_body: LoginRequest, request: Request, db: DbSession):
    """Authenticate user with email and password."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(request_body.email)

    if not user or not verify_password(request_body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    await user_repo.update_last_login(user.id)
    role = Role(user.role)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.USER_LOGIN,
        org_id=user.org_id,
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    logger.info("user_login", user_id=str(user.id))

    token_pair = create_token_pair(str(user.id), str(user.org_id), role)
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request_body: RefreshTokenRequest, db: DbSession):
    """Exchange a refresh token for a new token pair."""
    payload = decode_token(request_body.refresh_token)

    if payload.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type — expected refresh token",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload.sub))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_pair = create_token_pair(payload.sub, payload.org_id, Role(payload.role))
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_profile(
    db: DbSession,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get the current user's profile from the database."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(current_user.sub))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request_body: UserUpdateRequest,
    db: DbSession,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update the current user's profile."""
    user_repo = UserRepository(db)

    update_data = request_body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    user = await user_repo.update(uuid.UUID(current_user.sub), **update_data)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.USER_UPDATE,
        org_id=uuid.UUID(current_user.org_id),
        user_id=uuid.UUID(current_user.sub),
        resource_type="user",
        resource_id=current_user.sub,
        details={"updated_fields": list(update_data.keys())},
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
