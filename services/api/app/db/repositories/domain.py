"""
Aegis AI — Domain-Specific Repositories.

Each repository extends BaseRepository with domain-specific query methods.
Repositories are the only way the application layer accesses the database,
enforcing clean architecture boundaries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentRun, ApprovalRequest, AuditLog, Conversation, Document,
    DocumentChunk, Incident, IncidentEvent, Integration,
    Memory, Message, Organization, User, Workflow, WorkflowRun,
)
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(and_(User.email == email, User.deleted_at.is_(None)))
        )
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.update(user_id, last_login_at=datetime.now(UTC))

    async def get_by_id_with_org(self, user_id: uuid.UUID) -> User | None:
        """Fetch user with organization eagerly loaded."""
        result = await self.session.execute(
            select(User).where(
                and_(User.id == user_id, User.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(
                and_(Organization.slug == slug, Organization.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        *,
        status_filter: list[str] | None = None,
        severity_filter: list[str] | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Incident], int]:
        """List incidents with optional filtering by status and severity."""
        filters: dict[str, Any] = {"org_id": org_id}
        if status_filter:
            filters["status"] = status_filter
        if severity_filter:
            filters["severity"] = severity_filter
        return await self.list(
            filters=filters, offset=offset, limit=limit,
            order_by="created_at", order_dir="desc",
        )

    async def get_with_timeline(self, incident_id: uuid.UUID) -> Incident | None:
        """Fetch incident with timeline events eagerly loaded."""
        result = await self.session.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        incident = result.scalar_one_or_none()
        if incident:
            events_result = await self.session.execute(
                select(IncidentEvent)
                .where(IncidentEvent.incident_id == incident_id)
                .order_by(IncidentEvent.created_at)
            )
            incident.timeline_events = list(events_result.scalars().all())
        return incident

    async def count_by_status(self, org_id: uuid.UUID) -> dict[str, int]:
        """Get incident counts grouped by status for dashboard metrics."""
        result = await self.session.execute(
            select(Incident.status, func.count())
            .where(Incident.org_id == org_id)
            .group_by(Incident.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_by_severity(self, org_id: uuid.UUID) -> dict[str, int]:
        """Get incident counts grouped by severity."""
        result = await self.session.execute(
            select(Incident.severity, func.count())
            .where(Incident.org_id == org_id)
            .group_by(Incident.severity)
        )
        return {row[0]: row[1] for row in result.all()}


class IncidentEventRepository(BaseRepository[IncidentEvent]):
    model = IncidentEvent

    async def list_for_incident(self, incident_id: uuid.UUID) -> list[IncidentEvent]:
        result = await self.session.execute(
            select(IncidentEvent)
            .where(IncidentEvent.incident_id == incident_id)
            .order_by(IncidentEvent.created_at)
        )
        return list(result.scalars().all())


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Conversation], int]:
        return await self.list(
            filters={"user_id": user_id}, offset=offset, limit=limit,
        )

    async def get_with_messages(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            msg_result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            conv.messages = list(msg_result.scalars().all())
        return conv


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def list_for_conversation(
        self, conversation_id: uuid.UUID
    ) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())


class AgentRunRepository(BaseRepository[AgentRun]):
    model = AgentRun

    async def get_active_runs(self, org_id: uuid.UUID) -> list[AgentRun]:
        result = await self.session.execute(
            select(AgentRun).where(
                and_(AgentRun.org_id == org_id, AgentRun.status.in_(["running", "pending"]))
            )
        )
        return list(result.scalars().all())


class ApprovalRepository(BaseRepository[ApprovalRequest]):
    model = ApprovalRequest

    async def get_pending(self, org_id: uuid.UUID) -> list[ApprovalRequest]:
        result = await self.session.execute(
            select(ApprovalRequest).where(
                and_(ApprovalRequest.org_id == org_id, ApprovalRequest.status == "pending")
            ).order_by(ApprovalRequest.created_at.desc())
        )
        return list(result.scalars().all())


class DocumentRepository(BaseRepository[Document]):
    model = Document


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    model = DocumentChunk

    async def similarity_search(
        self,
        embedding: list[float],
        *,
        org_id: uuid.UUID | None = None,
        limit: int = 10,
        threshold: float = 0.72,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Perform vector similarity search using pgvector cosine distance.
        Returns chunks with their similarity scores.
        """
        query = (
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("similarity"),
            )
            .where(DocumentChunk.embedding.isnot(None))
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        if org_id:
            query = query.join(Document).where(Document.org_id == org_id)

        result = await self.session.execute(query)
        rows = result.all()
        return [(row[0], row[1]) for row in rows if row[1] >= threshold]


class IntegrationRepository(BaseRepository[Integration]):
    model = Integration

    async def get_by_type(self, org_id: uuid.UUID, type: str) -> list[Integration]:
        result = await self.session.execute(
            select(Integration).where(
                and_(Integration.org_id == org_id, Integration.type == type)
            )
        )
        return list(result.scalars().all())


class WorkflowRepository(BaseRepository[Workflow]):
    model = Workflow


class WorkflowRunRepository(BaseRepository[WorkflowRun]):
    model = WorkflowRun


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def log_action(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.create(
            org_id=org_id, user_id=user_id, action=action,
            resource_type=resource_type, resource_id=resource_id,
            details=details or {}, ip_address=ip_address, user_agent=user_agent,
        )

    async def list_for_org(
        self,
        org_id: uuid.UUID,
        *,
        action_filter: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """List audit logs with optional action filtering."""
        filters: dict[str, Any] = {"org_id": org_id}
        if action_filter:
            filters["action"] = action_filter
        return await self.list(
            filters=filters, offset=offset, limit=limit,
            order_by="timestamp", order_dir="desc",
        )


class MemoryRepository(BaseRepository[Memory]):
    model = Memory

    async def recall(
        self,
        embedding: list[float],
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID,
        limit: int = 5,
    ) -> list[Memory]:
        """Retrieve relevant memories using semantic similarity."""
        query = (
            select(Memory)
            .where(
                and_(
                    Memory.org_id == org_id,
                    Memory.embedding.isnot(None),
                    Memory.expires_at.is_(None) | (Memory.expires_at > datetime.now(UTC)),
                )
            )
            .order_by(Memory.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        if user_id:
            query = query.where(Memory.user_id == user_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())
