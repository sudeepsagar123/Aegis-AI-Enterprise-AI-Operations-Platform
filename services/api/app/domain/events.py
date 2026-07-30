"""
Aegis AI — Domain Events.

Defines the event contract for the event-driven architecture.
Events are published by domain operations and consumed by
handlers in the application layer.

Design Decision:
    Events are plain dataclasses rather than Pydantic models to keep
    the domain layer free of external dependencies. The application
    layer handles serialization when publishing to Redis/Kafka.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str = ""

    @property
    def event_type(self) -> str:
        """Returns the fully qualified event type name."""
        return f"{self.__class__.__module__}.{self.__class__.__qualname__}"


# ── User Events ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    user_id: str = ""
    org_id: str = ""
    email: str = ""
    role: str = ""


@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    user_id: str = ""
    ip_address: str = ""
    user_agent: str = ""


# ── Incident Events ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IncidentCreated(DomainEvent):
    incident_id: str = ""
    org_id: str = ""
    title: str = ""
    severity: str = ""
    source: str = ""


@dataclass(frozen=True)
class IncidentUpdated(DomainEvent):
    incident_id: str = ""
    org_id: str = ""
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IncidentAssigned(DomainEvent):
    incident_id: str = ""
    org_id: str = ""
    assignee_id: str = ""
    assigned_by: str = ""


@dataclass(frozen=True)
class IncidentResolved(DomainEvent):
    incident_id: str = ""
    org_id: str = ""
    resolved_by: str = ""
    resolution: str = ""


# ── Agent Events ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentRunStarted(DomainEvent):
    agent_run_id: str = ""
    agent_type: str = ""
    org_id: str = ""
    conversation_id: str = ""


@dataclass(frozen=True)
class AgentRunCompleted(DomainEvent):
    agent_run_id: str = ""
    agent_type: str = ""
    status: str = ""
    duration_ms: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ApprovalRequired(DomainEvent):
    approval_id: str = ""
    agent_run_id: str = ""
    action_type: str = ""
    risk_level: str = ""


# ── Knowledge Events ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DocumentIngested(DomainEvent):
    document_id: str = ""
    org_id: str = ""
    title: str = ""
    chunk_count: int = 0
