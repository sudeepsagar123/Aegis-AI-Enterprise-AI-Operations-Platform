"""
Unit tests for the LangGraph Multi-Agent Orchestrator.
"""

from __future__ import annotations

import pytest
from app.agents.orchestrator import (
    OrchestratorState,
    build_agent_graph,
    planner_node,
    executor_node,
    reviewer_node,
    reporter_node,
    approval_gate_node,
    route_next_agent,
)
from langchain_core.messages import HumanMessage, AIMessage


# ── Planner Node Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_planner_creates_plan():
    state: OrchestratorState = {
        "messages": [HumanMessage(content="Investigate CPU spike on prod-01")],
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await planner_node(state)
    assert "plan" in result
    assert len(result["plan"]) > 0
    assert result["next_agent"] == "executor"


@pytest.mark.asyncio
async def test_planner_handles_greetings():
    state: OrchestratorState = {
        "messages": [HumanMessage(content="hi")],
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await planner_node(state)
    assert result["next_agent"] == "end"
    assert "Aegis AI" in result["final_response"] or "Hello" in result["final_response"]


@pytest.mark.asyncio
async def test_planner_plan_has_required_fields():
    state: OrchestratorState = {
        "messages": [HumanMessage(content="Check database health")],
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await planner_node(state)
    for step in result["plan"]:
        assert "action" in step
        assert "tool" in step
        assert "description" in step
        assert "risk_level" in step


# ── Executor Node Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executor_runs_step():
    state: OrchestratorState = {
        "messages": [],
        "plan": [
            {"step": 1, "action": "search", "tool": "knowledge_base",
             "description": "Search KB", "risk_level": "low", "requires_approval": False},
        ],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await executor_node(state)
    assert result["current_step"] == 1
    assert result["next_agent"] == "reviewer"
    assert len(result["step_results"]) == 1


@pytest.mark.asyncio
async def test_executor_routes_to_reporter_when_done():
    state: OrchestratorState = {
        "messages": [],
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await executor_node(state)
    assert result["next_agent"] == "reporter"


@pytest.mark.asyncio
async def test_executor_requests_approval_for_high_risk():
    state: OrchestratorState = {
        "messages": [],
        "plan": [
            {"step": 1, "action": "deploy", "tool": "kubernetes",
             "description": "Restart pod", "risk_level": "critical", "requires_approval": True},
        ],
        "current_step": 0,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await executor_node(state)
    assert result["needs_approval"] is True
    assert result["next_agent"] == "approval_gate"


# ── Reviewer Node Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reviewer_continues_when_steps_remain():
    state: OrchestratorState = {
        "messages": [],
        "plan": [{"step": 1}, {"step": 2}],
        "current_step": 1,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await reviewer_node(state)
    assert result["next_agent"] == "executor"


@pytest.mark.asyncio
async def test_reviewer_routes_to_reporter_when_all_done():
    state: OrchestratorState = {
        "messages": [],
        "plan": [{"step": 1}],
        "current_step": 1,
        "step_results": [],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await reviewer_node(state)
    assert result["next_agent"] == "reporter"


# ── Reporter Node Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reporter_generates_response():
    state: OrchestratorState = {
        "messages": [],
        "plan": [],
        "current_step": 0,
        "step_results": [{"step": 0, "status": "completed", "data": {"result": "ok"}}],
        "needs_approval": False,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await reporter_node(state)
    assert result["final_response"] != ""
    assert result["next_agent"] == "end"
    assert "Report" in result["final_response"] or "Executive Summary" in result["final_response"]


# ── Approval Gate Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approval_gate_auto_approves():
    state: OrchestratorState = {
        "messages": [],
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "needs_approval": True,
        "approval_decision": None,
        "context": [],
        "entities": [],
        "memories": [],
        "final_response": "",
        "metadata": {},
        "error": None,
        "next_agent": "",
    }
    result = await approval_gate_node(state)
    assert result["needs_approval"] is False
    assert result["approval_decision"] == "approved"
    assert result["next_agent"] == "executor"


# ── Routing Logic Tests ──────────────────────────────────────────────────────


def test_route_to_executor():
    state = {"next_agent": "executor"}
    assert route_next_agent(state) == "executor"


def test_route_to_end():
    from langgraph.graph import END
    state = {"next_agent": "end"}
    assert route_next_agent(state) == END


def test_route_default_end():
    from langgraph.graph import END
    state = {}
    assert route_next_agent(state) == END


# ── Graph Construction Tests ─────────────────────────────────────────────────


def test_graph_builds_successfully():
    graph = build_agent_graph()
    assert graph is not None
