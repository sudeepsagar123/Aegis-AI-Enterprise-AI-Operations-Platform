# ============================================================================
# Aegis AI — Makefile
# ============================================================================

.PHONY: dev test test-unit test-int lint format db-migrate db-seed docs build deploy clean

# ── Development ──────────────────────────────────────────────────────────────

dev: ## Start all services in development mode
	docker compose up -d
	@echo "Services starting..."
	@echo "  API:        http://localhost:8000"
	@echo "  Frontend:   http://localhost:3000"
	@echo "  Grafana:    http://localhost:3001"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Jaeger:     http://localhost:16686"
	@echo "  MinIO:      http://localhost:9001"
	@echo "  Qdrant:     http://localhost:6333/dashboard"

dev-api: ## Start API server locally (requires postgres, redis running)
	cd services/api && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend locally
	cd frontend && npm run dev

# ── Testing ──────────────────────────────────────────────────────────────────

test: test-unit ## Run all tests

test-unit: ## Run unit tests
	cd services/api && poetry run pytest tests/unit -v --tb=short

test-int: ## Run integration tests (requires docker services)
	cd services/api && poetry run pytest tests/integration -v --tb=short

test-cov: ## Run tests with coverage report
	cd services/api && poetry run pytest tests/ -v --cov=app --cov-report=html --cov-report=xml

# ── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Run linters
	cd services/api && poetry run ruff check .

format: ## Auto-format code
	cd services/api && poetry run ruff format .
	cd services/api && poetry run ruff check --fix .

type-check: ## Run type checker
	cd services/api && poetry run mypy app/ --ignore-missing-imports

security-scan: ## Run security scanner
	cd services/api && poetry run bandit -r app/ -ll -q

# ── Database ─────────────────────────────────────────────────────────────────

db-migrate: ## Run database migrations
	cd services/api && poetry run alembic upgrade head

db-migrate-create: ## Create a new migration (usage: make db-migrate-create msg="add users table")
	cd services/api && poetry run alembic revision --autogenerate -m "$(msg)"

db-downgrade: ## Rollback last migration
	cd services/api && poetry run alembic downgrade -1

db-seed: ## Seed demo data
	cd services/api && poetry run python -m app.db.seed

# ── Docker ───────────────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker compose build

build-prod: ## Build production Docker images
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

down: ## Stop all services
	docker compose down

clean: ## Stop services and remove volumes
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

logs: ## Tail logs for all services
	docker compose logs -f

logs-api: ## Tail API logs
	docker compose logs -f api

# ── Documentation ────────────────────────────────────────────────────────────

docs: ## Generate API documentation
	@echo "API docs available at http://localhost:8000/docs"

# ── Deployment ───────────────────────────────────────────────────────────────

deploy-staging: ## Deploy to staging
	kubectl apply -k k8s/overlays/staging/

deploy-production: ## Deploy to production
	kubectl apply -k k8s/overlays/production/

# ── Help ─────────────────────────────────────────────────────────────────────

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
