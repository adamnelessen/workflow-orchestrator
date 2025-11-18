.PHONY: venv install clean test test-unit test-integration test-db test-postgres test-redis test-persistence test-e2e test-e2e-up test-e2e-down test-e2e-logs test-cov test-watch lint run-coordinator run-worker docker-build docker-up docker-down docker-db-only db-init db-demo db-test db-reset fresh-start submit-workflow workflow-demo help

# Default target - show help
.DEFAULT_GOAL := help

# Help command - shows all available targets with descriptions
help:
	@echo "Workflow Orchestrator - Available Make Commands"
	@echo "================================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install         - Install dependencies in virtual environment"
	@echo "  make install-dev     - Install with development dependencies"
	@echo "  make reinstall       - Clean and reinstall from scratch"
	@echo "  make clean           - Remove virtual environment and cache files"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-init         - Setup databases and initialize schema"
	@echo "  make db-demo         - Run database persistence demo"
	@echo "  make db-test         - Run database-specific tests"
	@echo "  make db-reset        - Stop databases and remove volumes"
	@echo "  make docker-db-only  - Start only PostgreSQL + Redis"
	@echo "  make fresh-start     - Complete fresh start (clean + setup + demo)"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-up       - Start all services (coordinator + workers + databases)"
	@echo "  make docker-down     - Stop all services"
	@echo "  make docker-logs     - View Docker logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests (includes databases)"
	@echo "  make test-unit       - Run unit tests only (fast, no databases)"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-db         - Run database integration tests (PostgreSQL + Redis)"
	@echo "  make test-e2e        - Run end-to-end tests"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo "  make lint            - Run linters (ruff, mypy)"
	@echo ""
	@echo "Examples:"
	@echo "  make submit-workflow - Submit example workflow"
	@echo "  make workflow-demo   - Run workflow demo"
	@echo ""

# Create virtual environment
venv:
	python3 -m venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"

# Install dependencies
install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e .

# Install with dev dependencies
install-dev: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

# Clean up virtual environment and cache files
clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -f .coverage

# Reinstall everything from scratch
reinstall: clean install

# Run all tests (includes integration tests with databases)
test: install-dev docker-db-only
	@echo "Running all tests (unit + integration + e2e)..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/ -v

# Run unit tests only (fast, no database required)
test-unit: install-dev
	@echo "Running unit tests only (no database required)..."
	.venv/bin/pytest tests/unit/ -v

# Run integration tests only (requires databases)
test-integration: install-dev docker-db-only
	@echo "Running integration tests (requires databases)..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/integration/ -v

# Run E2E tests (starts and stops docker environment)
test-e2e: install-dev
	@echo "Running end-to-end tests..."
	.venv/bin/pytest tests/e2e/ -v -s

# Start E2E test environment (without running tests)
test-e2e-up:
	docker-compose -f tests/e2e/docker-compose.e2e.yml up -d --build

# Stop E2E test environment
test-e2e-down:
	docker-compose -f tests/e2e/docker-compose.e2e.yml down -v

# View E2E environment logs
test-e2e-logs:
	docker-compose -f tests/e2e/docker-compose.e2e.yml logs -f

# Run tests with coverage report
test-cov: install-dev docker-db-only
	@echo "Running tests with coverage..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/ --cov=coordinator --cov=worker --cov=shared --cov=client --cov-report=html --cov-report=term

# Run a single test file (usage: make test-file FILE=tests/unit/test_scheduler.py)
test-file:
	.venv/bin/pytest $(FILE) -v

# Run tests in watch mode (requires pytest-watch)
test-watch:
	.venv/bin/ptw tests/

# Lint code
lint:
	.venv/bin/ruff check .
	.venv/bin/mypy .

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Start only databases (PostgreSQL + Redis)
docker-db-only:
	docker-compose up -d postgres redis
	@echo "Waiting for databases to be ready..."
	@sleep 3
	@docker-compose exec -T postgres pg_isready -U workflow || (echo "Waiting for PostgreSQL..." && sleep 2)
	@docker-compose exec -T redis redis-cli ping > /dev/null || (echo "Waiting for Redis..." && sleep 2)
	@echo "✅ Databases are ready!"

# Initialize database schema
db-init: install docker-db-only
	@echo "Initializing database schema..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/0 && \
	.venv/bin/python scripts/init_db.py
	@echo "✅ Database initialization complete!"

# Run database demo
db-demo: db-init
	@echo "Running database persistence demo..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/0 && \
	.venv/bin/python examples/database_demo.py

# Run database-specific tests
db-test: install
	.venv/bin/pytest tests/unit/test_state_manager_db.py -v

# Run database integration tests (requires PostgreSQL + Redis)
test-db: install-dev docker-db-only
	@echo "Running database integration tests..."
	@echo "Note: Tests require PostgreSQL and Redis to be running"
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/integration/test_postgres_integration.py tests/integration/test_redis_integration.py tests/integration/test_state_manager_persistence.py -v

# Run PostgreSQL integration tests only
test-postgres: install-dev docker-db-only
	@echo "Running PostgreSQL integration tests..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	.venv/bin/pytest tests/integration/test_postgres_integration.py -v

# Run Redis integration tests only
test-redis: install-dev docker-db-only
	@echo "Running Redis integration tests..."
	@export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/integration/test_redis_integration.py -v

# Run StateManager persistence tests (full stack)
test-persistence: install-dev docker-db-only
	@echo "Running StateManager persistence tests..."
	@export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator && \
	export REDIS_URL=redis://localhost:6379/1 && \
	.venv/bin/pytest tests/integration/test_state_manager_persistence.py -v -s

# Reset databases (stop and remove volumes)
db-reset:
	@echo "Stopping databases and removing volumes..."
	docker-compose stop postgres redis
	docker-compose rm -f postgres redis
	docker volume rm workflow-orchestrator_postgres_data workflow-orchestrator_redis_data 2>/dev/null || true
	@echo "✅ Databases reset complete!"

# Fresh start - complete clean setup and demo
fresh-start: clean docker-down
	@echo "🚀 Starting fresh setup..."
	@make install
	@make db-init
	@echo ""
	@echo "🎉 Fresh start complete! Running demo..."
	@echo ""
	@make db-demo
	@echo ""
	@echo "✅ All set! You can now:"
	@echo "   - Run 'make docker-up' to start the full system"
	@echo "   - Run 'make test' to run tests"
	@echo "   - Check 'make help' for more commands"

# Example workflow scripts (requires coordinator and workers to be running)
# Usage: make submit-workflow [WORKFLOW=data-processing-pipeline.yaml]
submit-workflow:
	.venv/bin/python -m examples.submit_workflow $(WORKFLOW)

workflow-demo:
	.venv/bin/python -m examples.workflow_demo
