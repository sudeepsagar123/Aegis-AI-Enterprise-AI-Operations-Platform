"""
Aegis AI — Audit Logging Service.

Application-layer service that records security-relevant events
to the append-only audit_logs table for SOC 2 compliance.

Design Decision:
    Audit logging is a cross-cutting concern wrapped in a service class
    (not a middleware) so it can be called with full business context
    (resource type, resource ID, action details) rather than just
    HTTP request metadata.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.domain import AuditLogRepository
from app.domain.enums import AuditAction

logger = get_logger(__name__)


class AuditService:
    """
    Records audit events for compliance and security monitoring.

    Every state-mutating operation should call this service to create
    an immutable audit trail. Events cannot be modified or deleted.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditLogRepository(session)

    async def log(
        self,
        *,
        action: AuditAction | str,
        org_id: uuid.UUID,
        resource_type: str,
        resource_id: str,
        user_id: uuid.UUID | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Record an audit event.

        Args:
            action: The action being performed (from AuditAction enum).
            org_id: The organization context.
            resource_type: Type of resource being acted upon.
            resource_id: ID of the specific resource.
            user_id: The user performing the action (None for system actions).
            details: Additional context for the event.
            ip_address: Client IP address.
            user_agent: Client user agent string.
        """
        action_str = action.value if isinstance(action, AuditAction) else action

        await self._repo.log_action(
            org_id=org_id,
            user_id=user_id,
            action=action_str,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            "audit_event",
            action=action_str,
            org_id=str(org_id),
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=str(user_id) if user_id else None,
        )
