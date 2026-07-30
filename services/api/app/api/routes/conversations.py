"""
Aegis AI — Conversation & Chat Routes.

Handles conversation CRUD and streaming AI chat with SSE.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    ConversationCreate, ConversationDetailResponse, ConversationResponse,
    MessageCreate, MessageResponse, PaginatedResponse, StreamEvent,
)
from app.core.logging import get_logger
from app.core.security import Permission, TokenPayload, get_current_user, require_permission
from app.db.repositories.domain import ConversationRepository, MessageRepository
from app.db.session import DbSession

logger = get_logger(__name__)
router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    offset: int = 0,
    limit: int = 20,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_READ)),
):
    """List all conversations for the current user."""
    repo = ConversationRepository(db)
    items, total = await repo.list_for_user(
        uuid.UUID(user.sub), offset=offset, limit=limit,
    )

    return PaginatedResponse(
        items=[
            ConversationResponse(
                id=c.id, title=c.title, status=c.status,
                tags=c.tags or [], summary=c.summary,
                created_at=c.created_at, updated_at=c.updated_at,
                message_count=len(c.messages) if hasattr(c, "messages") and c.messages else 0,
            )
            for c in items
        ],
        total=total, offset=offset, limit=limit, has_more=(offset + limit) < total,
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_CREATE)),
):
    """Create a new conversation."""
    repo = ConversationRepository(db)
    conv = await repo.create(
        user_id=uuid.UUID(user.sub),
        org_id=uuid.UUID(user.org_id),
        title=request.title,
        tags=request.tags,
        metadata_=request.metadata,
    )

    logger.info("conversation_created", conversation_id=str(conv.id), user_id=user.sub)

    return ConversationResponse(
        id=conv.id, title=conv.title, status=conv.status,
        tags=conv.tags or [], summary=conv.summary,
        created_at=conv.created_at, updated_at=conv.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_READ)),
):
    """Get a conversation with all messages."""
    repo = ConversationRepository(db)
    conv = await repo.get_with_messages(conversation_id)

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if str(conv.user_id) != user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return ConversationDetailResponse(
        id=conv.id, title=conv.title, status=conv.status,
        tags=conv.tags or [], summary=conv.summary,
        created_at=conv.created_at, updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                id=m.id, role=m.role, content=m.content, model=m.model,
                token_count=m.token_count, cost_usd=m.cost_usd,
                tool_calls=m.tool_calls, citations=m.citations,
                created_at=m.created_at,
            )
            for m in (conv.messages or [])
        ],
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    request: MessageCreate,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_CREATE)),
):
    """
    Send a message and get an AI response (non-streaming).

    For streaming responses, use POST /{conversation_id}/stream instead.
    """
    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)

    conv = await conv_repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Store user message
    user_msg = await msg_repo.create(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
    )

    # In production, this would invoke the LangGraph agent pipeline.
    # For now, we create a placeholder response.
    assistant_msg = await msg_repo.create(
        conversation_id=conversation_id,
        role="assistant",
        content="I'm processing your request. The full agent pipeline would execute here.",
        model="gpt-4o",
    )

    return MessageResponse(
        id=assistant_msg.id, role=assistant_msg.role, content=assistant_msg.content,
        model=assistant_msg.model, token_count=assistant_msg.token_count,
        cost_usd=assistant_msg.cost_usd, tool_calls=assistant_msg.tool_calls,
        citations=assistant_msg.citations, created_at=assistant_msg.created_at,
    )


@router.post("/{conversation_id}/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    request: MessageCreate,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_CREATE)),
):
    """
    Send a message and stream the AI response via Server-Sent Events.

    Event types:
    - token: Individual token from the LLM
    - tool_call: Agent is calling a tool
    - tool_result: Tool execution result
    - approval_needed: Human approval required
    - done: Stream complete
    - error: An error occurred
    """
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    async def event_generator() -> AsyncGenerator[dict, None]:
        """
        Generate SSE events from the LangGraph agent execution.

        In production, this connects to the agent orchestrator and
        streams tokens, tool calls, and approval requests in real-time.
        """
        try:
            # Emit thinking indicator
            yield {
                "event": "token",
                "data": json.dumps({"content": "Analyzing your request", "done": False}),
            }

            # Simulate tool call
            yield {
                "event": "tool_call",
                "data": json.dumps({
                    "tool": "search_knowledge_base",
                    "input": {"query": request.content},
                }),
            }

            yield {
                "event": "tool_result",
                "data": json.dumps({
                    "tool": "search_knowledge_base",
                    "result": {"documents_found": 3},
                }),
            }

            # Stream response tokens
            response_text = (
                "Based on my analysis of the connected systems and knowledge base, "
                "here is what I found regarding your query."
            )
            words = response_text.split()
            for i, word in enumerate(words):
                yield {
                    "event": "token",
                    "data": json.dumps({
                        "content": word + " ",
                        "done": i == len(words) - 1,
                    }),
                }

            # Done
            yield {
                "event": "done",
                "data": json.dumps({
                    "message_id": str(uuid.uuid4()),
                    "model": "gpt-4o",
                    "tokens_used": 150,
                    "cost_usd": 0.0045,
                }),
            }

        except Exception as e:
            logger.error("stream_error", error=str(e), conversation_id=str(conversation_id))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.CONVERSATION_DELETE)),
):
    """Soft-delete a conversation."""
    repo = ConversationRepository(db)
    conv = await repo.get_by_id(conversation_id)

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if str(conv.user_id) != user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await repo.delete(conversation_id, soft=True)
    logger.info("conversation_deleted", conversation_id=str(conversation_id))
