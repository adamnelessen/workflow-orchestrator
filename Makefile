.PHONY: venv install clean test test-unit test-integration test-cov test-watch lint run-coordinator run-worker docker-build docker-up docker-down submit-workflow workflow-demo

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
submit-workflow:
	.venv/bin/python -m examples.submit_workflow

workflow-demo:
	.venv/bin/python -m examples.workflow_demo
