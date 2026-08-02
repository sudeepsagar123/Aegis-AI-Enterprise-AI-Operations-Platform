# Aegis AI — Enterprise AI Operations Platform

[![CI/CD](https://github.com/sudeepsagar123/Aegis-AI-Enterprise-AI-Operations-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/sudeepsagar123/Aegis-AI-Enterprise-AI-Operations-Platform/actions)
[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![Test Coverage](https://img.shields.io/badge/tests-60%2B%20passed-brightgreen.svg)](#testing)

> **Aegis AI** is a production-grade, multi-agent AI operations platform that connects to enterprise systems, understands business operations, investigates issues autonomously, and assists operators through structured reasoning — all while maintaining SOC 2-compliant security, horizontal scalability, and full observability.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AEGIS AI — SYSTEM OVERVIEW                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │   Next.js    │   │  Slack Bot   │   │   REST API   │   Channels     │
│  │   Dashboard  │   │  Interface   │   │   Clients    │                │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                │
│         │                  │                   │                        │
│  ───────┴──────────────────┴───────────────────┴────── API Gateway ──  │
│                            │                                            │
│  ┌─────────────────────────┴─────────────────────────┐                 │
│  │              FastAPI Application Layer             │                 │
│  │  ┌────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐  │                 │
│  │  │ Auth   │ │ Incident │ │ Chat    │ │Knowledge│  │                 │
│  │  │ RBAC   │ │ Center   │ │ Service │ │ Base   │  │                 │
│  │  └────────┘ └──────────┘ └─────────┘ └────────┘  │                 │
│  └─────────────────────────┬─────────────────────────┘                 │
│                            │                                            │
│  ┌─────────────────────────┴─────────────────────────┐                 │
│  │             AI Orchestration Layer (LangGraph)      │                 │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐       │                 │
│  │  │ Planner  │ │ Executor │ │  Reviewer    │       │                 │
│  │  │ Agent    │ │ Agent    │ │  Agent       │       │                 │
│  │  └──────────┘ └──────────┘ └──────────────┘       │                 │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │                 │
│  │  │ Reporter │ │ Approval │ │ Tool Registry    │   │                 │
│  │  │ Agent    │ │ Gate     │ │ (MCP-compatible) │   │                 │
│  │  └──────────┘ └──────────┘ └──────────────────┘   │                 │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │                 │
│  │  │ RAG      │ │ Webhook  │ │ Memory Manager   │   │                 │
│  │  │ Pipeline │ │ Service  │ │                  │   │                 │
│  │  └──────────┘ └──────────┘ └──────────────────┘   │                 │
│  └───────────────────────────────────────────────────┘                 │
│                            │                                            │
│  ┌─────────────────────────┴─────────────────────────┐                 │
│  │               Data & Integration Layer             │                 │
│  │  ┌──────┐  ┌───────┐ ┌───────┐ ┌────────┐         │                 │
│  │  │Postgres│ │ Redis │ │Qdrant │ │ MinIO  │         │                 │
│  │  └──────┘  └───────┘ └───────┘ └────────┘         │                 │
│  └───────────────────────────────────────────────────┘                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────┐                 │
│  │            Observability & Security                │                 │
│  │  OpenTelemetry · Prometheus · Grafana · Jaeger    │                 │
│  │  JWT/RBAC · Audit Logging · Rate Limiting         │                 │
│  │  HMAC Webhook Signing · Correlation ID Tracing    │                 │
│  └───────────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 14, React 18, TypeScript 5, Tailwind CSS, Radix UI, Zustand, TanStack Query |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| **AI/ML** | LangGraph (multi-agent), LangChain, OpenAI, Anthropic, Gemini, Groq, Ollama |
| **Database** | PostgreSQL 16 (pgvector), Redis 7, Qdrant (vector search) |
| **Storage** | MinIO (S3-compatible object storage) |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Jaeger, structlog |
| **Security** | JWT (HS256/RS256), RBAC (6 roles, 21 permissions), bcrypt, SOC 2 audit logging |
| **Notifications** | Webhook service (Slack, PagerDuty, Teams, OpsGenie), SSE streaming |
| **Infrastructure** | Docker, Kubernetes, Terraform, GitHub Actions CI/CD, NGINX |

---

## Quick Start

### Local Development (No Docker Required)

```bash
# Clone the repository
git clone https://github.com/sudeepsagar123/Aegis-AI-Enterprise-AI-Operations-Platform.git
cd Aegis-AI-Enterprise-AI-Operations-Platform

# Create Python virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r services/api/requirements.txt

# Run the demo server (SQLite, no external services needed)
python run_demo_server.py

# Access the platform
# API Docs:  http://localhost:8000/docs
# Health:    http://localhost:8000/health
# Metrics:   http://localhost:8000/metrics
```

### Run the Live Demo Script

```bash
python demo_live_execution.py
```

This executes a complete 7-step operational flow:

1. **System Health Probe** → `GET /health` → 200 OK
2. **User Registration** → `POST /api/v1/auth/register` → JWT token pair
3. **Profile & RBAC** → `GET /api/v1/auth/me` → role, permissions
4. **Create Incident** → `POST /api/v1/incidents` → critical severity
5. **Dashboard Stats** → `GET /api/v1/incidents/stats` → by severity/status
6. **List Incidents** → `GET /api/v1/incidents` → paginated
7. **Prometheus Metrics** → `GET /metrics` → telemetry stream

### Full Stack (Docker Compose)

```bash
cp .env.example .env
docker compose up -d
make db-migrate
make db-seed

# API:      http://localhost:8000/docs
# Frontend: http://localhost:3000
# Grafana:  http://localhost:3001
```

### Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@acme.com | Admin@123! |
| Operator | operator@acme.com | Operator@123! |
| Viewer | viewer@acme.com | Viewer@123! |

---

## Repository Structure

```
aegis-ai/
├── services/
│   └── api/                          # FastAPI backend
│       ├── app/
│       │   ├── agents/               # AI agent implementations
│       │   │   ├── orchestrator.py    # LangGraph multi-agent state graph
│       │   │   └── tools.py          # MCP-compatible tool registry
│       │   ├── api/                   # Presentation layer
│       │   │   ├── routes/            # Auth, incidents, conversations, knowledge, approvals
│       │   │   └── schemas.py         # Pydantic v2 request/response schemas
│       │   ├── core/                  # Cross-cutting concerns
│       │   │   ├── config.py          # Settings (Pydantic BaseSettings)
│       │   │   ├── security.py        # JWT, RBAC, bcrypt
│       │   │   ├── llm.py            # Multi-LLM provider router
│       │   │   ├── metrics.py        # Prometheus business metrics
│       │   │   ├── middleware.py      # Rate limiter, correlation ID
│       │   │   └── logging.py        # Structured logging (structlog)
│       │   ├── db/                    # Data layer
│       │   │   ├── models.py          # 19 SQLAlchemy 2.0 ORM models
│       │   │   ├── session.py        # Async engine factory
│       │   │   ├── seed.py           # Demo data seeder
│       │   │   └── repositories/     # Repository pattern (base + domain)
│       │   ├── domain/               # Domain enums and events
│       │   │   └── enums.py          # Roles, Permissions, Severity, Status
│       │   ├── services/             # Application services
│       │   │   ├── audit.py          # SOC 2 compliance audit logging
│       │   │   ├── rag_pipeline.py   # Hybrid RAG (vector + BM25 + RRF)
│       │   │   └── webhooks.py       # Webhook delivery (Slack/PD/Teams)
│       │   └── main.py              # FastAPI application factory
│       ├── alembic/                  # Database migrations
│       ├── tests/                    # Test suite (60+ tests)
│       │   ├── unit/                 # Unit tests
│       │   └── integration/          # Integration tests
│       └── requirements.txt          # Pinned dependencies
├── frontend/                         # Next.js 14 dashboard
│   ├── src/app/                     # App router pages
│   └── package.json                 # Node dependencies
├── k8s/                             # Kubernetes manifests
│   └── base/                        # Deployments, services, ingress
├── terraform/                       # Infrastructure as Code
│   └── environments/                # Production Terraform configs
├── monitoring/                      # Observability configs
│   └── prometheus/                  # Prometheus scrape configs
├── scripts/                         # Database init, utilities
├── docs/                            # Architecture docs, ADRs
│   └── adr/                         # Architecture Decision Records
├── docker-compose.yml               # Development orchestration
├── Makefile                         # Developer commands
├── run_demo_server.py               # Local demo server launcher
├── demo_live_execution.py           # E2E API demo script
└── .github/workflows/               # CI/CD pipeline
```

---

## Multi-Agent Architecture

Aegis AI uses a **LangGraph state graph** with a Planner → Executor → Reviewer → Reporter pattern:

```
                    ┌──────────┐
                    │  Planner │ ← Decomposes request into risk-assessed steps
                    └────┬─────┘
                         │
                    ┌────▼─────┐
               ┌──→ │ Executor │ ← Invokes tools (Jira, Slack, GitHub, SQL, KB)
               │    └────┬─────┘
               │         │
               │    ┌────▼──────────┐
               │    │ Approval Gate │ ← Pauses on high/critical risk actions
               │    └────┬──────────┘
               │         │
               │    ┌────▼─────┐
               └──← │ Reviewer │ ← Validates results, loops or continues
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Reporter │ ← Synthesizes findings with citations
                    └──────────┘
```

### Supported LLM Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| OpenAI | gpt-4o, gpt-4o-mini | Primary reasoning |
| Anthropic | claude-3.5-sonnet, claude-3.5-haiku | Complex analysis |
| Google | gemini-2.0-flash, gemini-1.5-pro | Multi-modal |
| Groq | llama-3.3-70b | Fast inference |
| Ollama | Local models | Air-gapped deployments |

---

## API Reference

Interactive Swagger documentation: `http://localhost:8000/docs`

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Register organization + admin user |
| `POST` | `/api/v1/auth/login` | Authenticate → JWT access + refresh |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Current user profile & RBAC role |

### Incident Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/incidents` | Create incident |
| `GET` | `/api/v1/incidents` | List incidents (paginated, filterable) |
| `GET` | `/api/v1/incidents/stats` | Dashboard metrics (by severity/status) |
| `GET` | `/api/v1/incidents/{id}` | Get incident detail + timeline |
| `PATCH` | `/api/v1/incidents/{id}` | Update incident |
| `POST` | `/api/v1/incidents/{id}/assign` | Assign to operator |

### AI Conversations

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/conversations` | Create conversation |
| `GET` | `/api/v1/conversations` | List conversations |
| `POST` | `/api/v1/conversations/{id}/messages` | Send message (non-streaming) |
| `POST` | `/api/v1/conversations/{id}/stream` | Stream response via SSE |

### Knowledge Base

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/knowledge/search` | Hybrid RAG search |
| `POST` | `/api/v1/knowledge/ingest` | Ingest document |

### Observability

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/readiness` | Readiness probe (DB connectivity) |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Testing

```bash
# Run all tests
pytest services/api/tests

# Run with verbose output
pytest services/api/tests -v

# Run specific test module
pytest services/api/tests/unit/test_auth.py -v
pytest services/api/tests/unit/test_orchestrator.py -v
pytest services/api/tests/unit/test_webhooks.py -v
```

### Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| Authentication & RBAC | 17 | ✅ All pass |
| Middleware (Rate Limiting, Correlation ID) | 4 | ✅ All pass |
| RAG Pipeline (Chunker, RRF) | 9 | ✅ All pass |
| LLM Router | 4 | ✅ All pass |
| Agent Orchestrator | 12 | ✅ All pass |
| Webhook Service | 15 | ✅ All pass |
| Integration (Health, Auth, API) | 7 | ✅ All pass |

---

## Security

- **Authentication**: JWT access/refresh tokens (HS256), 30-minute access TTL
- **Authorization**: 6-tier RBAC hierarchy with 21 granular permissions
- **Password Storage**: Direct bcrypt hashing with 72-byte truncation
- **Rate Limiting**: Token-bucket per IP (configurable)
- **Audit Trail**: Append-only `audit_logs` table (SOC 2 compliant)
- **Webhook Signing**: HMAC-SHA256 payload signatures
- **Tenant Isolation**: All queries scoped by `org_id`

---

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](docs/adr/001-multi-agent-architecture.md) | Multi-Agent Architecture (LangGraph) | Accepted |

---

## License

This project is licensed under the [Business Source License 1.1](LICENSE).
