"""
Aegis AI — LangGraph Multi-Agent Orchestrator.

Implements the core agent graph with Planner → Executor → Reviewer pattern.
Agents collaborate through a shared state graph with tool calling,
human-in-the-loop checkpoints, and streaming output.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Agent State ──────────────────────────────────────────────────────────────


class AgentState:
    """
    Shared state for the multi-agent graph.

    Using TypedDict-style annotation for LangGraph state channels.
    """
    pass


# We define state as a dict for LangGraph compatibility
from typing import TypedDict


class OrchestratorState(TypedDict):
    """Shared state flowing through the agent graph."""
    # Conversation messages (accumulated via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]
    # Current plan from the Planner agent
    plan: list[dict[str, Any]]
    # Current step index in the plan
    current_step: int
    # Results from executed steps
    step_results: list[dict[str, Any]]
    # Whether human approval is needed
    needs_approval: bool
    # Approval decision
    approval_decision: str | None
    # Retrieved context from RAG
    context: list[dict[str, Any]]
    # Knowledge graph entities
    entities: list[dict[str, Any]]
    # Memories recalled
    memories: list[dict[str, Any]]
    # Final response
    final_response: str
    # Metadata
    metadata: dict[str, Any]
    # Error state
    error: str | None
    # Which agent should run next
    next_agent: str


# ── Agent Prompts ────────────────────────────────────────────────────────────


PLANNER_SYSTEM_PROMPT = """You are the Planner Agent in the Aegis AI operations platform.

Your role is to analyze the user's request and create a structured execution plan.
You have access to enterprise systems: Jira, Slack, GitHub, Salesforce, SAP, databases,
and a knowledge base of organizational documents.

For each step in your plan, specify:
1. action: The type of action (search, query, create, update, analyze, notify)
2. tool: Which tool/integration to use
3. description: What this step accomplishes
4. risk_level: low, medium, high, critical
5. requires_approval: Whether human approval is needed (true for high/critical risk)

Output your plan as a JSON array of steps.
Always prefer the least-disruptive approach. Explain your reasoning."""

EXECUTOR_SYSTEM_PROMPT = """You are the Executor Agent in the Aegis AI operations platform.

Your role is to execute individual steps from the plan created by the Planner.
You have access to tools for interacting with enterprise systems.

Execute the current step precisely as planned. Report:
1. What was done
2. What data was retrieved or modified
3. Any errors or unexpected results

Be thorough in your execution but conservative in your actions."""

REVIEWER_SYSTEM_PROMPT = """You are the Reviewer Agent in the Aegis AI operations platform.

Your role is to review the results of executed steps and determine:
1. Was the step executed correctly?
2. Are the results consistent with the plan?
3. Should the plan be adjusted based on new information?
4. Is there sufficient evidence to answer the user's question?
5. Are there any security or compliance concerns?

Provide a clear assessment and recommendation for next steps."""

REPORTER_SYSTEM_PROMPT = """You are the Reporter Agent in the Aegis AI operations platform.

Your role is to synthesize all investigation results into a clear, actionable response.
Structure your response with:
1. Executive Summary
2. Key Findings
3. Root Cause (if applicable)
4. Recommendations
5. Evidence & Citations

Use data from the executed steps and knowledge base to support your conclusions.
Always cite your sources. Be concise but thorough."""


# ── Agent Node Functions ─────────────────────────────────────────────────────


async def planner_node(state: OrchestratorState) -> dict:
    """
    Planner Agent: Analyzes the request and creates an execution plan.
    """
    logger.info("planner_executing", message_count=len(state["messages"]))

    # In production: call LLM with the planner prompt and tools
    # For now, create a simple plan based on the last message
    last_message = state["messages"][-1] if state["messages"] else None

    plan = [
        {
            "step": 1,
            "action": "search",
            "tool": "knowledge_base",
            "description": "Search knowledge base for relevant information",
            "risk_level": "low",
            "requires_approval": False,
        },
        {
            "step": 2,
            "action": "analyze",
            "tool": "reasoning",
            "description": "Analyze retrieved information and formulate response",
            "risk_level": "low",
            "requires_approval": False,
        },
    ]

    return {
        "plan": plan,
        "current_step": 0,
        "next_agent": "executor",
        "messages": [AIMessage(content=f"Plan created with {len(plan)} steps.")],
    }


async def executor_node(state: OrchestratorState) -> dict:
    """
    Executor Agent: Executes the current step in the plan.
    """
    current_step = state.get("current_step", 0)
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"next_agent": "reporter", "messages": []}

    step = plan[current_step]
    logger.info("executor_running_step", step=current_step, action=step["action"])

    # Check if approval is needed
    if step.get("requires_approval"):
        return {
            "needs_approval": True,
            "next_agent": "approval_gate",
            "messages": [AIMessage(
                content=f"Step {current_step + 1} requires approval: {step['description']}"
            )],
        }

    # In production: execute the actual tool call
    result = {
        "step": current_step,
        "status": "completed",
        "data": {"result": f"Executed: {step['description']}"},
    }

    return {
        "step_results": [*state.get("step_results", []), result],
        "current_step": current_step + 1,
        "next_agent": "reviewer",
        "messages": [AIMessage(content=f"Step {current_step + 1} completed: {step['description']}")],
    }


async def reviewer_node(state: OrchestratorState) -> dict:
    """
    Reviewer Agent: Reviews execution results and decides next action.
    """
    current_step = state.get("current_step", 0)
    plan = state.get("plan", [])

    logger.info("reviewer_evaluating", step=current_step, total_steps=len(plan))

    # If all steps are done, go to reporter
    if current_step >= len(plan):
        return {
            "next_agent": "reporter",
            "messages": [AIMessage(content="All steps completed. Generating report.")],
        }

    # Otherwise, continue execution
    return {
        "next_agent": "executor",
        "messages": [AIMessage(content=f"Step review passed. Proceeding to step {current_step + 1}.")],
    }


async def reporter_node(state: OrchestratorState) -> dict:
    """
    Reporter Agent: Synthesizes results into a final response.
    """
    logger.info("reporter_generating", results_count=len(state.get("step_results", [])))

    # In production: LLM call with all step results to generate comprehensive response
    final_response = (
        "## Investigation Complete\n\n"
        "Based on my analysis across connected systems, here are the findings:\n\n"
        "### Key Findings\n"
        "- Analysis of the knowledge base and connected systems completed\n"
        "- All investigation steps executed successfully\n\n"
        "### Recommendations\n"
        "- Detailed recommendations would be generated based on actual data\n"
    )

    return {
        "final_response": final_response,
        "next_agent": "end",
        "messages": [AIMessage(content=final_response)],
    }


async def approval_gate_node(state: OrchestratorState) -> dict:
    """
    Approval Gate: Pauses execution for human-in-the-loop review.

    In production, this creates an ApprovalRequest in the database
    and notifies via Slack/UI. The graph pauses until the user responds.
    """
    logger.info("approval_gate_waiting")

    # In production: create approval request and use LangGraph checkpointing
    # For now, auto-approve
    return {
        "needs_approval": False,
        "approval_decision": "approved",
        "next_agent": "executor",
        "messages": [AIMessage(content="Action approved. Continuing execution.")],
    }


# ── Routing Logic ────────────────────────────────────────────────────────────


def route_next_agent(state: OrchestratorState) -> str:
    """Route to the next agent based on state."""
    next_agent = state.get("next_agent", "end")
    if next_agent == "end":
        return END
    return next_agent


# ── Graph Construction ───────────────────────────────────────────────────────


def build_agent_graph() -> StateGraph:
    """
    Build the multi-agent orchestration graph.

    Graph topology:
        planner → executor → reviewer → executor (loop) → reporter → END
                     ↓
              approval_gate (if needed)
                     ↓
                  executor (resume)
    """
    graph = StateGraph(OrchestratorState)

    # Add agent nodes
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("reporter", reporter_node)
    graph.add_node("approval_gate", approval_gate_node)

    # Set entry point
    graph.set_entry_point("planner")

    # Add conditional edges based on next_agent routing
    graph.add_conditional_edges("planner", route_next_agent)
    graph.add_conditional_edges("executor", route_next_agent)
    graph.add_conditional_edges("reviewer", route_next_agent)
    graph.add_conditional_edges("reporter", route_next_agent)
    graph.add_conditional_edges("approval_gate", route_next_agent)

    return graph.compile()


# Module-level compiled graph
agent_graph = build_agent_graph()
