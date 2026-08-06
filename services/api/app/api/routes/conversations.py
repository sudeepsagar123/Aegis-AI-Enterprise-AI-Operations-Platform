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
        conv = await conv_repo.create(
            id=conversation_id,
            user_id=uuid.UUID(user.sub),
            org_id=uuid.UUID(user.org_id),
            title=request.content[:30] if request.content else "Interactive Agent Chat",
            status="active",
        )

    # Store user message
    user_msg = await msg_repo.create(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
    )

    # Load past conversation history
    from langchain_core.messages import HumanMessage as HMsg, AIMessage as AMsg
    past_messages = await msg_repo.list_for_conversation(conversation_id)
    langchain_messages = []
    for pm in past_messages:
        if pm.role == "user":
            langchain_messages.append(HMsg(content=pm.content))
        elif pm.role == "assistant":
            langchain_messages.append(AMsg(content=pm.content))

    if not langchain_messages:
        langchain_messages = [HMsg(content=request.content)]

    # Invoke the LangGraph agent pipeline
    from app.agents.orchestrator import agent_graph, OrchestratorState

    initial_state: OrchestratorState = {
        "messages": langchain_messages,
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {"conversation_id": str(conversation_id)},
        "error": None,
        "next_agent": "",
    }

    # Run the full agent graph
    final_state = await agent_graph.ainvoke(initial_state)
    agent_response = final_state.get("final_response", "Investigation complete. No additional findings.")
    step_results = final_state.get("step_results", [])

    # Extract dynamic executed tools for frontend badges
    executed_tools = []
    for sr in step_results:
        t_name = sr.get("tool", "")
        if t_name and t_name not in [t["name"] for t in executed_tools]:
            executed_tools.append({"name": t_name, "status": "completed"})

    if not executed_tools:
        executed_tools = [
            {"name": "planner", "status": "completed"},
            {"name": "executor", "status": "completed"},
            {"name": "reporter", "status": "completed"}
        ]

    tool_calls_payload = {"items": executed_tools}

    assistant_msg = await msg_repo.create(
        conversation_id=conversation_id,
        role="assistant",
        content=agent_response,
        model="aegis-agent-graph",
        tool_calls=tool_calls_payload,
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
        Streams agent reasoning, tool calls, and final report in real-time.
        """
        try:
            from app.agents.orchestrator import agent_graph, OrchestratorState
            from langchain_core.messages import HumanMessage as HMsg

            # Emit thinking indicator
            yield {
                "event": "token",
                "data": json.dumps({"content": "🔍 Initiating agent investigation...\n\n", "done": False}),
            }

            # Build initial state
            initial_state: OrchestratorState = {
                "messages": [HMsg(content=request.content)],
                "plan": [],
                "current_step": 0,
                "step_results": [],
                "needs_approval": False,
                "approval_decision": None,
                "context": [],
                "entities": [],
                "memories": [],
                "final_response": "",
                "metadata": {"conversation_id": str(conversation_id)},
                "error": None,
                "next_agent": "",
            }

            # Run the agent graph and stream each node's output
            final_response = ""
            async for event in agent_graph.astream(initial_state):
                for node_name, node_output in event.items():
                    # Stream agent messages as tokens
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            content = msg.content if hasattr(msg, "content") else str(msg)
                            if content:
                                yield {
                                    "event": "token",
                                    "data": json.dumps({"content": f"**[{node_name.upper()}]**\n{content}\n\n", "done": False}),
                                }

                    # Track tool calls
                    if "step_results" in node_output:
                        for result in node_output.get("step_results", []):
                            yield {
                                "event": "tool_result",
                                "data": json.dumps({
                                    "tool": result.get("tool", "unknown"),
                                    "result": result.get("data", {}),
                                }),
                            }

                    # Capture final response
                    if "final_response" in node_output and node_output["final_response"]:
                        final_response = node_output["final_response"]

            # Done
            yield {
                "event": "done",
                "data": json.dumps({
                    "message_id": str(uuid.uuid4()),
                    "model": "aegis-agent-graph",
                    "tokens_used": 0,
                    "cost_usd": 0.0,
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
