.PHONY: venv install clean test lint run-coordinator run-worker docker-build docker-up docker-down

# Create virtual environment
venv:
	python3 -m venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"

# Install dependencies
install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

# Install with dev dependencies (if you add them later)
install-dev: install
	.venv/bin/pip install -r requirements-dev.txt

# Clean up virtual environment and cache files
clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Reinstall everything from scratch
reinstall: clean install

# Run tests
test:
	.venv/bin/pytest tests/

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
