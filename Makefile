# ──────────────────────────────────────────────────────────
# Vibe — Session Architect
# ──────────────────────────────────────────────────────────

BOLD   := \033[1m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
CYAN   := \033[36m
RESET  := \033[0m

DC := docker compose

.PHONY: help
help: ## Show this help
	@printf "$(BOLD)$(CYAN)Vibe — Session Architect$(RESET)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(RESET) %s\n", $$1, $$2}'

# ──────────────────────────────────────────────────────────
# Full Stack
# ──────────────────────────────────────────────────────────

.PHONY: start stop restart build rebuild logs ps

start: ## Start all services
	@printf "$(BOLD)$(GREEN)Starting all services...$(RESET)\n"
	$(DC) up -d
	@printf "$(BOLD)$(GREEN)All services started$(RESET)\n"
	@printf "  Backend:  $(CYAN)http://localhost:8000$(RESET)\n"
	@printf "  Frontend: $(CYAN)http://localhost:5173$(RESET)\n"

stop: ## Stop all services
	@printf "$(BOLD)$(YELLOW)Stopping all services...$(RESET)\n"
	$(DC) down

restart: stop start ## Restart all services

build: ## Build all containers
	@printf "$(BOLD)$(GREEN)Building all containers...$(RESET)\n"
	$(DC) build

rebuild: ## Rebuild all containers (no cache)
	@printf "$(BOLD)$(GREEN)Rebuilding all containers (no cache)...$(RESET)\n"
	$(DC) build --no-cache

logs: ## Tail all logs
	$(DC) logs -f

ps: ## Show running services
	$(DC) ps

# ──────────────────────────────────────────────────────────
# Backend
# ──────────────────────────────────────────────────────────

.PHONY: start-backend stop-backend build-backend logs-backend shell-backend

start-backend: ## Start backend only
	@printf "$(BOLD)$(GREEN)Starting backend...$(RESET)\n"
	$(DC) up -d backend

stop-backend: ## Stop backend only
	$(DC) stop backend

build-backend: ## Build backend container
	$(DC) build backend

logs-backend: ## Tail backend logs
	$(DC) logs -f backend

shell-backend: ## Shell into backend container
	$(DC) exec backend bash

# ──────────────────────────────────────────────────────────
# Frontend
# ──────────────────────────────────────────────────────────

.PHONY: start-frontend stop-frontend build-frontend logs-frontend shell-frontend

start-frontend: ## Start frontend only
	@printf "$(BOLD)$(GREEN)Starting frontend...$(RESET)\n"
	$(DC) up -d frontend

stop-frontend: ## Stop frontend only
	$(DC) stop frontend

build-frontend: ## Build frontend container
	$(DC) build frontend

logs-frontend: ## Tail frontend logs
	$(DC) logs -f frontend

shell-frontend: ## Shell into frontend container
	$(DC) exec frontend sh

# ──────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────

.PHONY: start-db stop-db db-shell db-migrate db-migration db-downgrade db-reset

start-db: ## Start PostgreSQL
	$(DC) up -d postgres

stop-db: ## Stop PostgreSQL
	$(DC) stop postgres

db-shell: ## Open psql shell
	$(DC) exec postgres psql -U vibe -d vibe

db-migrate: ## Run all pending migrations
	@printf "$(BOLD)$(GREEN)Running migrations...$(RESET)\n"
	$(DC) exec backend alembic upgrade head

db-migration: ## Create a new migration (MESSAGE="description")
	@printf "$(BOLD)$(GREEN)Creating migration: $(MESSAGE)$(RESET)\n"
	$(DC) exec backend alembic revision --autogenerate -m "$(MESSAGE)"

db-downgrade: ## Downgrade one migration
	@printf "$(BOLD)$(YELLOW)Downgrading one migration...$(RESET)\n"
	$(DC) exec backend alembic downgrade -1

db-reset: ## Reset database (DESTRUCTIVE)
	@printf "$(BOLD)$(RED)Resetting database...$(RESET)\n"
	$(DC) down -v postgres
	$(DC) up -d postgres
	@sleep 3
	$(DC) exec backend alembic upgrade head
	@printf "$(BOLD)$(GREEN)Database reset complete$(RESET)\n"

# ──────────────────────────────────────────────────────────
# Redis
# ──────────────────────────────────────────────────────────

.PHONY: start-redis stop-redis redis-cli

start-redis: ## Start Redis
	$(DC) up -d redis

stop-redis: ## Stop Redis
	$(DC) stop redis

redis-cli: ## Open Redis CLI
	$(DC) exec redis redis-cli

# ──────────────────────────────────────────────────────────
# Local Development (no Docker)
# ──────────────────────────────────────────────────────────

.PHONY: setup-backend setup-frontend run-backend-local run-frontend-local

setup-backend: ## Set up backend venv + deps
	@printf "$(BOLD)$(GREEN)Setting up backend...$(RESET)\n"
	cd backend && python3 -m venv .venv && \
		.venv/bin/pip install --upgrade pip && \
		.venv/bin/pip install -r requirements.txt
	@printf "$(BOLD)$(GREEN)Backend ready. Activate: source backend/.venv/bin/activate$(RESET)\n"

setup-frontend: ## Install frontend deps
	@printf "$(BOLD)$(GREEN)Setting up frontend...$(RESET)\n"
	cd frontend && npm install
	@printf "$(BOLD)$(GREEN)Frontend ready$(RESET)\n"

run-backend-local: ## Run backend locally (no Docker)
	cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-frontend-local: ## Run frontend locally (no Docker)
	cd frontend && npm run dev

# ──────────────────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────────────────

.PHONY: test test-cov test-backend test-frontend lint format

test: ## Run all tests
	@printf "$(BOLD)$(GREEN)Running all tests...$(RESET)\n"
	cd backend && python -m pytest tests/ -v
	cd frontend && npm test -- --run

test-backend: ## Run backend tests only
	cd backend && python -m pytest tests/ -v

test-frontend: ## Run frontend tests only
	cd frontend && npm test -- --run

test-cov: ## Run tests with coverage
	cd backend && python -m pytest tests/ -v --cov=src --cov-report=html
	@printf "$(BOLD)$(GREEN)Coverage report: backend/htmlcov/index.html$(RESET)\n"

lint: ## Lint backend code
	cd backend && ruff check src/ tests/

format: ## Format backend code
	cd backend && ruff format src/ tests/

# ──────────────────────────────────────────────────────────
# Maintenance
# ──────────────────────────────────────────────────────────

.PHONY: clean clean-docker clean-all

clean: ## Remove Python/Node caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/coverage

clean-docker: ## Remove Docker volumes
	@printf "$(BOLD)$(RED)Removing Docker volumes...$(RESET)\n"
	$(DC) down -v --remove-orphans

clean-all: clean clean-docker ## Remove everything
	@printf "$(BOLD)$(RED)Full clean complete$(RESET)\n"
