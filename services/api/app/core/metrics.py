"""
Aegis AI — Prometheus Business Metrics Service.

Exposes application-level metrics beyond the default Python runtime metrics.
These enable Grafana dashboards with real-time operational KPIs.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ── Application Info ─────────────────────────────────────────────────────────

APP_INFO = Info(
    "aegis_ai",
    "Aegis AI platform metadata",
)
APP_INFO.info({
    "version": "0.1.0",
    "component": "api",
    "framework": "fastapi",
})

# ── Authentication Metrics ───────────────────────────────────────────────────

AUTH_LOGIN_TOTAL = Counter(
    "aegis_auth_login_total",
    "Total login attempts",
    ["status", "method"],
)

AUTH_REGISTRATION_TOTAL = Counter(
    "aegis_auth_registration_total",
    "Total user registrations",
    ["status"],
)

AUTH_TOKEN_REFRESH_TOTAL = Counter(
    "aegis_auth_token_refresh_total",
    "Total token refresh attempts",
    ["status"],
)

ACTIVE_SESSIONS = Gauge(
    "aegis_active_sessions",
    "Currently active user sessions",
    ["org_id"],
)

# ── Incident Metrics ────────────────────────────────────────────────────────

INCIDENTS_CREATED_TOTAL = Counter(
    "aegis_incidents_created_total",
    "Total incidents created",
    ["severity", "source"],
)

INCIDENTS_RESOLVED_TOTAL = Counter(
    "aegis_incidents_resolved_total",
    "Total incidents resolved",
    ["severity"],
)

INCIDENTS_OPEN = Gauge(
    "aegis_incidents_open",
    "Currently open incidents",
    ["severity"],
)

INCIDENT_MTTR_SECONDS = Histogram(
    "aegis_incident_mttr_seconds",
    "Mean Time To Resolve incidents (seconds)",
    ["severity"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400],
)

# ── Agent Execution Metrics ─────────────────────────────────────────────────

AGENT_RUNS_TOTAL = Counter(
    "aegis_agent_runs_total",
    "Total agent orchestration runs",
    ["agent_type", "status"],
)

AGENT_RUN_DURATION_SECONDS = Histogram(
    "aegis_agent_run_duration_seconds",
    "Agent run execution time",
    ["agent_type"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "aegis_agent_tool_calls_total",
    "Total tool invocations by agents",
    ["tool_name", "status"],
)

AGENT_APPROVAL_REQUESTS_TOTAL = Counter(
    "aegis_agent_approval_requests_total",
    "Total human-in-the-loop approval requests",
    ["risk_level", "decision"],
)

ACTIVE_AGENT_RUNS = Gauge(
    "aegis_active_agent_runs",
    "Currently running agent graphs",
)

# ── RAG Pipeline Metrics ────────────────────────────────────────────────────

RAG_QUERIES_TOTAL = Counter(
    "aegis_rag_queries_total",
    "Total RAG retrieval queries",
    ["search_method"],
)

RAG_QUERY_DURATION_SECONDS = Histogram(
    "aegis_rag_query_duration_seconds",
    "RAG query latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

RAG_DOCUMENTS_INGESTED_TOTAL = Counter(
    "aegis_rag_documents_ingested_total",
    "Total documents ingested into the knowledge base",
    ["source_type"],
)

RAG_CHUNKS_STORED_TOTAL = Counter(
    "aegis_rag_chunks_stored_total",
    "Total document chunks stored",
)

# ── LLM Provider Metrics ────────────────────────────────────────────────────

LLM_REQUESTS_TOTAL = Counter(
    "aegis_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],
)

LLM_TOKEN_USAGE_TOTAL = Counter(
    "aegis_llm_token_usage_total",
    "Total tokens consumed across LLM providers",
    ["provider", "model", "token_type"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "aegis_llm_request_duration_seconds",
    "LLM request latency",
    ["provider"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

LLM_COST_USD_TOTAL = Counter(
    "aegis_llm_cost_usd_total",
    "Total LLM API cost in USD",
    ["provider", "model"],
)

# ── Webhook Delivery Metrics ────────────────────────────────────────────────

WEBHOOK_DELIVERIES_TOTAL = Counter(
    "aegis_webhook_deliveries_total",
    "Total webhook delivery attempts",
    ["event_type", "destination", "status"],
)

WEBHOOK_DELIVERY_DURATION_SECONDS = Histogram(
    "aegis_webhook_delivery_duration_seconds",
    "Webhook delivery latency",
    ["destination"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Audit Log Metrics ───────────────────────────────────────────────────────

AUDIT_EVENTS_TOTAL = Counter(
    "aegis_audit_events_total",
    "Total SOC 2 audit events recorded",
    ["action", "resource_type"],
)

# ── Database Metrics ────────────────────────────────────────────────────────

DB_QUERY_DURATION_SECONDS = Histogram(
    "aegis_db_query_duration_seconds",
    "Database query latency",
    ["operation", "table"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "aegis_db_connection_pool_size",
    "Current database connection pool size",
    ["state"],
)
