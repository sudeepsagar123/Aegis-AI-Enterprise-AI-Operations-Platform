"""
Aegis AI — Pydantic API Schemas.

Request/response models for all API endpoints. Follows the principle of
separating API contracts from internal ORM models.

Design Decision:
    Schemas are grouped by domain (Auth, Incident, Conversation, etc.)
    and use Pydantic v2 with ConfigDict for ORM mode. Generic
    PaginatedResponse enables type-safe pagination across all endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field


T = TypeVar("T")


# ── Common ───────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    trace_id: str | None = None


# ── Auth ─────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    preferences: dict | None = None


# ── Incidents ────────────────────────────────────────────────────────────────


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    severity: str = Field(default="medium", pattern=r"^(critical|high|medium|low|info)$")
    source: str = Field(default="manual", pattern=r"^(manual|prometheus|grafana|datadog|pagerduty|slack|webhook|agent)$")
    tags: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = Field(default=None, pattern=r"^(critical|high|medium|low|info)$")
    status: str | None = Field(default=None, pattern=r"^(open|investigating|identified|monitoring|resolved|closed)$")
    root_cause: str | None = None
    resolution: str | None = None
    impact: str | None = None
    tags: list[str] | None = None
    affected_services: list[str] | None = None


class IncidentAssign(BaseModel):
    assignee_id: uuid.UUID


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    severity: str
    status: str
    source: str
    reported_by: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    root_cause: str | None = None
    resolution: str | None = None
    impact: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None = None
    actor_type: str
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class IncidentDetailResponse(IncidentResponse):
    timeline: list[IncidentEventResponse] = Field(default_factory=list)


class IncidentStatsResponse(BaseModel):
    by_status: dict[str, int]
    by_severity: dict[str, int]
    total: int


# ── Conversations ────────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    tags: list[str]
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    model: str | None = None
    token_count: int | None = None
    cost_usd: float | None = None
    tool_calls: dict | None = None
    citations: list[dict] | None = None
    created_at: datetime


# ── Agent Runs ───────────────────────────────────────────────────────────────


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_type: str
    status: str
    plan: dict | None = None
    duration_ms: int | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    created_at: datetime


class ToolExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_name: str
    tool_input: dict
    tool_output: dict | None = None
    status: str
    duration_ms: int | None = None
    created_at: datetime


# ── Approvals ────────────────────────────────────────────────────────────────


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_type: str
    action_description: str
    risk_level: str
    status: str
    created_at: datetime
    expires_at: datetime | None = None


class ApprovalDecision(BaseModel):
    approved: bool
    reason: str | None = None


# ── Knowledge ────────────────────────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_type: str
    processing_status: str
    chunk_count: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)
    source_types: list[str] | None = None
    threshold: float = Field(default=0.72, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    score: float
    source_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total_results: int


# ── Integrations ─────────────────────────────────────────────────────────────


class IntegrationCreate(BaseModel):
    type: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    name: str
    status: str
    last_health_check: datetime | None = None
    last_sync_at: datetime | None = None
    created_at: datetime


# ── Workflows ────────────────────────────────────────────────────────────────


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    trigger_type: str
    is_active: bool
    run_count: int
    last_run_at: datetime | None = None
    created_at: datetime


# ── Streaming ────────────────────────────────────────────────────────────────


class StreamEvent(BaseModel):
    """Server-Sent Event payload for streaming AI responses."""
    event: str  # "token", "tool_call", "tool_result", "approval_needed", "done", "error"
    data: dict[str, Any]
