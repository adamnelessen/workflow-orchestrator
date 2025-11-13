# Workflow Orchestrator

A distributed workflow orchestration system with coordinator and worker components.

## Setup

### Quick Start

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Using Make

```bash
# Install dependencies
make install

# Clean and reinstall everything
make reinstall

# Clean up
make clean
```

## Development

### Install development dependencies

```bash
pip install -r requirements-dev.txt
# or
make install-dev
```

### Running Tests

```bash
pytest tests/
# or
make test
```

### Linting

```bash
make lint
```

## Docker

### Build and run with Docker Compose

```bash
# Build containers
make docker-build

# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## Project Structure

```
workflow-orchestrator/
├── coordinator/       # Coordinator service
├── worker/           # Worker service
├── shared/           # Shared schemas and utilities
├── tests/            # Test files
└── docker/           # Docker configurations
```
