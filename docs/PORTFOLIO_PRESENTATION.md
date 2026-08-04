# Aegis AI — Portfolio & Architectural Walkthrough

> **Tagline**: *"A production-grade multi-agent AI operations platform for enterprise systems."*

---

## Executive Summary

Aegis AI is an enterprise-grade AI Operations (AIOps) platform built to automate incident investigation, system troubleshooting, and business workflow orchestration. Designed using modern microservices, stateful multi-agent graphs, and SOC 2 compliant governance, Aegis AI demonstrates real-world software engineering mastery across backend systems, distributed AI architecture, and full-stack integration.

---

## Top 5 Technical Highlights

### 1. LangGraph Multi-Agent Orchestrator
- **Architecture**: Stateful state machine featuring `Planner`, `Executor`, `Reviewer`, and `Reporter` nodes with conditional routing and Human-in-the-Loop (HITL) approval gates.
- **Resilience**: Dynamic plan adaptation based on tool feedback; fallback model execution across OpenAI, Anthropic, Gemini, Groq, and Ollama.

### 2. Hybrid RAG (Reciprocal Rank Fusion)
- **Search Mechanics**: Merges dense vector embeddings (Qdrant / pgvector) with sparse keyword matching (BM25).
- **Reranking**: Standardized Reciprocal Rank Fusion (RRF) algorithm to rank chunks dynamically before feeding agent context windows.

### 3. Multi-Dialect Database Abstraction
- **Portability**: Dialect-agnostic SQLAlchemy 2.0 models supporting seamless local SQLite execution alongside production PostgreSQL + pgvector deployment.

### 4. SOC 2 Compliant Security & Audit Trail
- **Authentication**: JWT access/refresh token rotation with native bcrypt password hashing.
- **RBAC**: 6 roles (`super_admin`, `org_admin`, `incident_manager`, `operator`, `viewer`, `service_account`) and 21 fine-grained permissions.
- **Auditability**: Immutable, append-only `audit_logs` service tracking every state mutation.

### 5. Outbound Webhook Delivery & Observability
- **Integrations**: Standardized payload formatters for Slack, PagerDuty Events API v2, and MS Teams Adaptive Cards.
- **Security**: HMAC-SHA256 payload signing for webhook endpoint verification.
- **Telemetry**: 30+ Prometheus business metrics (`/metrics`), OpenTelemetry distributed tracing context (`X-Correlation-ID`), structured JSON logging (`structlog`).

---

## Live System Demonstration Flow

To demonstrate the full platform end-to-end:

```bash
# 1. Run the local demo server
python run_demo_server.py

# 2. Run the automated 7-step E2E execution suite
python demo_live_execution.py

# 3. Run the full pytest test suite (79+ tests passing)
pytest services/api/tests -v
```

---

## System Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          AEGIS AI ARCHITECTURE                            │
├───────────────────────────────────────────────────────────────────────────┤
│  Client Tier        Next.js 14 Dashboard · Slack Bot · REST / SSE API      │
│  Gateway Tier       FastAPI · Security Headers · Rate Limiter · Tracing  │
│  AI Engine          LangGraph State Machine · Multi-LLM Provider Router   │
│  Knowledge Tier     Hybrid RAG (Vector + BM25 + Reciprocal Rank Fusion)   │
│  Data Layer         PostgreSQL (pgvector) · Redis · Qdrant · MinIO        │
│  Observability      Prometheus Metrics · OpenTelemetry · Structlog        │
└───────────────────────────────────────────────────────────────────────────┘
```
