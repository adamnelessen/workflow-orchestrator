.PHONY: venv install clean test test-unit test-integration test-e2e test-e2e-up test-e2e-down test-e2e-logs test-cov test-watch lint run-coordinator run-worker docker-build docker-up docker-down submit-workflow workflow-demo

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

# Run all tests
test:
	.venv/bin/pytest tests/ -v

# Run unit tests only
test-unit:
	.venv/bin/pytest tests/unit/ -v -m unit

# Run integration tests only
test-integration:
	.venv/bin/pytest tests/integration/ -v -m integration

# Run E2E tests (starts and stops docker environment)
test-e2e:
	.venv/bin/pytest tests/e2e/ -v -m e2e -s

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
test-cov:
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

# Example workflow scripts (requires coordinator and workers to be running)
# Usage: make submit-workflow [WORKFLOW=data-processing-pipeline.yaml]
submit-workflow:
	.venv/bin/python -m examples.submit_workflow $(WORKFLOW)

workflow-demo:
	.venv/bin/python -m examples.workflow_demo
