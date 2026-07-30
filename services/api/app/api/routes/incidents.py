"""
Aegis AI — Incident Management Routes.

Core API for the incident center — create, list, get, update, assign,
and track incident timelines. Every state change creates an immutable
timeline event for full auditability.

Architecture:
    Incidents are the primary work unit of the platform. They connect to:
    - AI agent investigations via conversation links
    - Audit logs for compliance
    - Timeline events for investigation history
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.schemas import (
    IncidentAssign, IncidentCreate, IncidentDetailResponse,
    IncidentEventResponse, IncidentResponse, IncidentStatsResponse,
    IncidentUpdate, PaginatedResponse,
)
from app.core.logging import get_logger
from app.core.security import TokenPayload, require_permission
from app.db.repositories.domain import IncidentEventRepository, IncidentRepository
from app.db.session import DbSession
from app.domain.enums import AuditAction, IncidentStatus, Permission
from app.services.audit import AuditService

logger = get_logger(__name__)
router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    request: IncidentCreate,
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_CREATE)),
):
    """
    Create a new incident.

    Incidents can be created manually by operators or automatically by
    monitoring integrations (Prometheus, Grafana, PagerDuty) via webhooks.
    """
    repo = IncidentRepository(db)
    event_repo = IncidentEventRepository(db)

    incident = await repo.create(
        org_id=uuid.UUID(user.org_id),
        title=request.title,
        description=request.description,
        severity=request.severity,
        status=IncidentStatus.OPEN.value,
        source=request.source,
        reported_by=uuid.UUID(user.sub),
        tags=request.tags,
        affected_services=request.affected_services,
        labels=request.labels,
    )

    # Create timeline event
    await event_repo.create(
        incident_id=incident.id,
        event_type="created",
        actor_id=uuid.UUID(user.sub),
        actor_type="user",
        content=f"Incident created with severity {request.severity}",
        metadata_={
            "severity": request.severity,
            "source": request.source,
        },
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.INCIDENT_CREATE,
        org_id=uuid.UUID(user.org_id),
        user_id=uuid.UUID(user.sub),
        resource_type="incident",
        resource_id=str(incident.id),
        details={"title": request.title, "severity": request.severity},
    )

    logger.info(
        "incident_created",
        incident_id=str(incident.id),
        severity=request.severity,
        user_id=user.sub,
    )

    return IncidentResponse.model_validate(incident)


@router.get("", response_model=PaginatedResponse[IncidentResponse])
async def list_incidents(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: list[str] | None = Query(None, alias="status"),
    severity_filter: list[str] | None = Query(None, alias="severity"),
    db: DbSession = None,  # type: ignore[assignment]
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """
    List incidents for the organization with optional filtering.

    Supports filtering by status and severity. Results are paginated
    and ordered by creation date (newest first).
    """
    repo = IncidentRepository(db)
    items, total = await repo.list_for_org(
        uuid.UUID(user.org_id),
        status_filter=status_filter,
        severity_filter=severity_filter,
        offset=offset,
        limit=limit,
    )

    return PaginatedResponse(
        items=[IncidentResponse.model_validate(i) for i in items],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.get("/stats", response_model=IncidentStatsResponse)
async def get_incident_stats(
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Get aggregated incident statistics for the dashboard."""
    repo = IncidentRepository(db)
    org_id = uuid.UUID(user.org_id)

    by_status = await repo.count_by_status(org_id)
    by_severity = await repo.count_by_severity(org_id)
    total = sum(by_status.values())

    return IncidentStatsResponse(
        by_status=by_status,
        by_severity=by_severity,
        total=total,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Get incident details with full investigation timeline."""
    repo = IncidentRepository(db)
    incident = await repo.get_with_timeline(incident_id)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    if str(incident.org_id) != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    timeline = [
        IncidentEventResponse(
            id=e.id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_type=e.actor_type,
            content=e.content,
            metadata_=e.metadata_,
            created_at=e.created_at,
        )
        for e in (incident.timeline_events or [])
    ]

    response = IncidentDetailResponse.model_validate(incident)
    response.timeline = timeline
    return response


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    request: IncidentUpdate,
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_UPDATE)),
):
    """
    Update incident fields.

    Status transitions trigger timeline events and, for resolution,
    auto-populate the resolved_at timestamp.
    """
    repo = IncidentRepository(db)
    event_repo = IncidentEventRepository(db)

    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if str(incident.org_id) != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build update kwargs from non-None fields
    update_data: dict[str, Any] = {}
    changes: dict[str, Any] = {}

    for field_name in request.model_fields_set:
        new_value = getattr(request, field_name)
        old_value = getattr(incident, field_name, None)
        if new_value != old_value:
            update_data[field_name] = new_value
            changes[field_name] = {"old": str(old_value), "new": str(new_value)}

    if not update_data:
        return IncidentResponse.model_validate(incident)

    # Handle status transition side effects
    new_status = update_data.get("status")
    if new_status:
        if new_status == IncidentStatus.RESOLVED.value and not incident.resolved_at:
            update_data["resolved_at"] = datetime.now(UTC)
        elif new_status == IncidentStatus.CLOSED.value and not incident.closed_at:
            update_data["closed_at"] = datetime.now(UTC)
        elif new_status == IncidentStatus.INVESTIGATING.value and not incident.acknowledged_at:
            update_data["acknowledged_at"] = datetime.now(UTC)

    updated = await repo.update(incident_id, **update_data)

    # Record timeline event
    await event_repo.create(
        incident_id=incident_id,
        event_type="status_change" if new_status else "updated",
        actor_id=uuid.UUID(user.sub),
        actor_type="user",
        content=f"Updated: {', '.join(changes.keys())}",
        metadata_=changes,
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.INCIDENT_UPDATE,
        org_id=uuid.UUID(user.org_id),
        user_id=uuid.UUID(user.sub),
        resource_type="incident",
        resource_id=str(incident_id),
        details=changes,
    )

    logger.info("incident_updated", incident_id=str(incident_id), changes=list(changes.keys()))
    return IncidentResponse.model_validate(updated)


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident(
    incident_id: uuid.UUID,
    request: IncidentAssign,
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_ASSIGN)),
):
    """Assign an incident to a team member."""
    repo = IncidentRepository(db)
    event_repo = IncidentEventRepository(db)

    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if str(incident.org_id) != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated = await repo.update(incident_id, assigned_to=request.assignee_id)

    # Timeline event
    await event_repo.create(
        incident_id=incident_id,
        event_type="assignment",
        actor_id=uuid.UUID(user.sub),
        actor_type="user",
        content=f"Assigned to {request.assignee_id}",
        metadata_={"assignee_id": str(request.assignee_id)},
    )

    # Audit log
    audit = AuditService(db)
    await audit.log(
        action=AuditAction.INCIDENT_ASSIGN,
        org_id=uuid.UUID(user.org_id),
        user_id=uuid.UUID(user.sub),
        resource_type="incident",
        resource_id=str(incident_id),
        details={"assignee_id": str(request.assignee_id)},
    )

    logger.info(
        "incident_assigned",
        incident_id=str(incident_id),
        assignee_id=str(request.assignee_id),
    )

    return IncidentResponse.model_validate(updated)


@router.get("/{incident_id}/timeline", response_model=list[IncidentEventResponse])
async def get_incident_timeline(
    incident_id: uuid.UUID,
    db: DbSession,
    user: TokenPayload = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Get the full investigation timeline for an incident."""
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if str(incident.org_id) != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    event_repo = IncidentEventRepository(db)
    events = await event_repo.list_for_incident(incident_id)

    return [
        IncidentEventResponse(
            id=e.id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_type=e.actor_type,
            content=e.content,
            metadata_=e.metadata_,
            created_at=e.created_at,
        )
        for e in events
    ]
