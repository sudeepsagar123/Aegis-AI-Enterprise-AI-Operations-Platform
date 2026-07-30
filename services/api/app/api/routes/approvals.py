"""
Aegis AI — Approval Routes (Human-in-the-Loop).

Manages approval requests for high-risk agent actions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import ApprovalDecision, ApprovalResponse, PaginatedResponse
from app.core.logging import get_logger
from app.core.security import Permission, TokenPayload, require_permission
from app.db.repositories.domain import ApprovalRepository
from app.db.session import DbSession

logger = get_logger(__name__)
router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=PaginatedResponse[ApprovalResponse])
async def list_pending_approvals(
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.AGENT_APPROVE)),
):
    """List all pending approval requests for the organization."""
    repo = ApprovalRepository(db)
    items = await repo.get_pending(uuid.UUID(user.org_id))

    return PaginatedResponse(
        items=[
            ApprovalResponse(
                id=a.id, action_type=a.action_type,
                action_description=a.action_description,
                risk_level=a.risk_level, status=a.status,
                created_at=a.created_at, expires_at=a.expires_at,
            )
            for a in items
        ],
        total=len(items), offset=0, limit=50, has_more=False,
    )


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: uuid.UUID,
    decision: ApprovalDecision,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.AGENT_APPROVE)),
):
    """Approve or reject a pending action."""
    repo = ApprovalRepository(db)
    approval = await repo.get_by_id(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")

    new_status = "approved" if decision.approved else "rejected"
    updated = await repo.update(
        approval_id,
        status=new_status,
        decided_by=uuid.UUID(user.sub),
        decided_at=datetime.now(UTC),
        decision_reason=decision.reason,
    )

    logger.info(
        "approval_decided",
        approval_id=str(approval_id),
        decision=new_status,
        decided_by=user.sub,
    )

    # In production: resume the agent run if approved
    # await agent_orchestrator.resume(approval.agent_run_id, approved=decision.approved)

    return ApprovalResponse(
        id=updated.id, action_type=updated.action_type,
        action_description=updated.action_description,
        risk_level=updated.risk_level, status=updated.status,
        created_at=updated.created_at, expires_at=updated.expires_at,
    )
