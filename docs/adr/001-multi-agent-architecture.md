# ADR-001: Multi-Agent Architecture

## Status

Accepted

## Context

Aegis AI needs to handle diverse enterprise operations tasks — incident investigation, log analysis, root cause analysis, deployment management, and knowledge retrieval. A monolithic AI approach would be:

1. **Fragile**: A single prompt handling all tasks leads to confusion and hallucination.
2. **Unscalable**: Cannot parallelize investigation steps.
3. **Unauditable**: Difficult to attribute actions to specific reasoning chains.

## Decision

We adopt a **multi-agent architecture** using LangGraph for orchestration:

### Agent Design Principles

1. **Single Responsibility**: Each agent specializes in one domain (incidents, logs, security, etc.)
2. **Explicit Tools**: Agents declare their tools upfront — no ad-hoc tool discovery.
3. **Structured Output**: Agents produce typed results, not free-form text.
4. **Memory Isolation**: Each agent maintains its own working memory during a run.
5. **Coordinator Pattern**: A coordinator agent routes tasks and synthesizes results.

### Agent Graph

```
User Query → Coordinator → [Planner → Executor → Reviewer]
                              ↓
              ┌─────────────────────────────────┐
              │  Specialist Agents (parallel)    │
              │  - Incident Agent                │
              │  - Log Analysis Agent            │
              │  - Monitoring Agent              │
              │  - Security Agent                │
              │  - Knowledge Agent               │
              └─────────────────────────────────┘
                              ↓
              Report Agent → Structured Output
```

### LangGraph State Machine

- **State**: Typed dataclass with conversation history, intermediate results, tool outputs
- **Nodes**: Each agent is a node in the graph
- **Edges**: Conditional routing based on task type and intermediate results
- **Checkpointing**: State is persisted to PostgreSQL for recovery and debugging

### Human-in-the-Loop

High-risk actions (deployments, data mutations, API calls) require human approval:
- Agent pauses execution and creates an `ApprovalRequest`
- Operator approves/rejects via UI or Slack
- Agent resumes or aborts based on decision

## Consequences

### Positive
- Clear separation of concerns per agent
- Parallel investigation speeds up incident resolution
- Full audit trail of agent reasoning
- Easy to add new specialist agents
- Human oversight for safety-critical actions

### Negative
- Higher token cost due to multi-agent coordination overhead
- More complex debugging (multiple reasoning chains)
- Latency from sequential agent handoffs

### Mitigations
- LLM response caching reduces redundant calls
- Async parallel execution where agents are independent
- Comprehensive observability with OpenTelemetry tracing
