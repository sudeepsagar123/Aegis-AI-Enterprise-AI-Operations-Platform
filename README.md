# Aegis AI — Enterprise AI Operations Platform

[![CI/CD](https://github.com/sudeepsagar123/Aegis-AI-Enterprise-AI-Operations-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/sudeepsagar123/Aegis-AI-Enterprise-AI-Operations-Platform/actions)
[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

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
│  │  │Coordinator│ │ Incident │ │Investigation │       │                 │
│  │  │ Agent    │ │ Agent    │ │ Agent        │       │                 │
│  │  └──────────┘ └──────────┘ └──────────────┘       │                 │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐       │                 │
│  │  │ Security │ │ Deploy   │ │  Knowledge   │       │                 │
│  │  │ Agent    │ │ Agent    │ │  Agent       │       │                 │
│  │  └──────────┘ └──────────┘ └──────────────┘       │                 │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │                 │
│  │  │ RAG      │ │ Memory   │ │ Tool Registry    │   │                 │
│  │  │ Pipeline │ │ Manager  │ │                  │   │                 │
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
│  └───────────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 14, React 18, TypeScript 5, Tailwind CSS, shadcn/ui |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Alembic |
| **AI** | LangGraph, LangChain, OpenAI, Anthropic, Gemini, Groq, Ollama |
| **Database** | PostgreSQL 16 (pgvector), Redis 7, Qdrant |
| **Storage** | MinIO (S3-compatible) |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Jaeger, structlog |
| **Security** | JWT, RBAC (6 roles, 21 permissions), bcrypt, audit logging |
| **Infrastructure** | Docker, Kubernetes, Terraform, GitHub Actions, NGINX |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/aegis-ai.git
cd aegis-ai

# Copy environment configuration
cp .env.example .env

# Start all services
docker compose up -d

# Run database migrations
make db-migrate

# Seed demo data
make db-seed

# Access the platform
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
│   └── api/                    # FastAPI backend
│       ├── app/
│       │   ├── domain/         # Domain layer (enums, events)
│       │   ├── core/           # Config, security, middleware, logging
│       │   ├── api/            # Routes and schemas (presentation)
│       │   │   └── routes/     # Auth, incidents, conversations, etc.
│       │   ├── db/             # Models, session, repositories
│       │   │   └── repositories/
│       │   ├── services/       # Application services (audit, etc.)
│       │   └── agents/         # AI agent implementations
│       ├── alembic/            # Database migrations
│       └── tests/              # Unit and integration tests
├── frontend/                   # Next.js dashboard
├── k8s/                        # Kubernetes manifests
├── terraform/                  # Infrastructure as Code
├── monitoring/                 # Prometheus, Grafana configs
├── scripts/                    # Database init, utilities
├── docs/                       # Architecture docs, ADRs
├── docker-compose.yml          # Development orchestration
├── Makefile                    # Developer commands
└── .github/workflows/          # CI/CD pipeline
```

---

## Development

```bash
make help          # Show all available commands
make dev           # Start all services
make test          # Run tests
make lint          # Run linters
make db-migrate    # Run migrations
make db-seed       # Seed demo data
make clean         # Remove all containers and volumes
```

---

## API Documentation

Interactive docs available at `http://localhost:8000/docs` when running locally.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register user + organization |
| POST | `/api/v1/auth/login` | Authenticate and get tokens |
| GET | `/api/v1/auth/me` | Get current user profile |
| POST | `/api/v1/incidents` | Create incident |
| GET | `/api/v1/incidents` | List incidents (filterable) |
| GET | `/api/v1/incidents/stats` | Dashboard statistics |
| PATCH | `/api/v1/incidents/{id}` | Update incident |
| POST | `/api/v1/incidents/{id}/assign` | Assign incident |
| GET | `/health` | Health check |
| GET | `/readiness` | Readiness probe |
| GET | `/metrics` | Prometheus metrics |

---

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](docs/adr/001-multi-agent-architecture.md) | Multi-Agent Architecture | Accepted |

---

## License

This project is licensed under the [Business Source License 1.1](LICENSE).
