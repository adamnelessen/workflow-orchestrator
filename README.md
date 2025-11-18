# Workflow Orchestrator

Production-grade distributed workflow orchestration with coordinator-worker architecture, hybrid persistence, and WebSocket-based communication.

## Quick Start

```bash
# Start everything (coordinator + workers + databases)
make quick-start

# Or step by step
make db-init          # Initialize databases
make docker-up        # Start all services
make submit-workflow  # Run example workflow
```

See [QUICKSTART.md](QUICKSTART.md) for detailed guide.

## Features

- **Distributed Execution**: Coordinator schedules jobs across worker pool
- **Hybrid Persistence**: Three-tier storage (memory → Redis → PostgreSQL)
- **WebSocket Communication**: Real-time bidirectional messaging
- **Resilient**: Automatic state recovery, worker failure handling
- **YAML Workflows**: Define complex DAGs with conditional execution
- **Observable**: REST API, metrics, comprehensive logging

## Architecture

- **Coordinator**: FastAPI service managing workflows, job scheduling, worker registry
- **Workers**: Asynchronous job processors with capability-based routing
- **Storage**: PostgreSQL (persistence), Redis (cache/coordination), Memory (hot path)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design.

## Setup

### Prerequisites
- Python 3.11+
- Docker & docker-compose (for databases)

### Installation

```bash
# Install with databases
make install

# Or development mode with test dependencies
make install-dev
```

### Run with Docker

```bash
# Full stack (recommended)
make docker-up
docker-compose logs -f

# Stop services
make docker-down
```

### Run Locally

```bash
# Start databases
docker-compose up -d postgres redis

# Initialize schema
make db-init

# Terminal 1: Coordinator
export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0
python -m coordinator.main

# Terminal 2: Worker
export COORDINATOR_URL=ws://localhost:8000/workers
export WORKER_ID=worker-1
python -m worker.main
```

## Workflow Definition

YAML format with conditional execution:

```yaml
workflow:
  name: "data-pipeline"
  jobs:
    - id: "validate"
      type: "validation"
      parameters:
        schema: "input-schema"
      on_success: "process"
      on_failure: "alert"
    
    - id: "process"
      type: "processing"
      parameters:
        operation: "transform"
      on_success: "save"
    
    - id: "save"
      type: "integration"
      parameters:
        endpoint: "data-store"
    
    - id: "alert"
      type: "integration"
      parameters:
        channel: "slack-alerts"
      always_run: true
```

### Job Types
- `validation`: Input validation, schema checks
- `processing`: Data transformation, computation
- `integration`: External API calls, storage operations
- `cleanup`: Resource cleanup, always-run tasks

Examples in `examples/workflow_definitions/`.

## API Usage

### Submit Workflow

```bash
curl -X POST http://localhost:8000/workflows/from-yaml \
  -H "Content-Type: text/plain" \
  --data-binary @workflow.yaml
```

### Start Workflow

```bash
curl -X POST http://localhost:8000/workflows/{workflow_id}/start
```

### Get Status

```bash
curl http://localhost:8000/workflows/{workflow_id}
```

### Python Client

```python
from client.workflow_client import WorkflowClient

client = WorkflowClient("http://localhost:8000")
workflow = client.submit_and_start_workflow("workflow.yaml")
print(f"Status: {workflow.status}")
```

## Database Commands

```bash
make db-init       # Initialize PostgreSQL schema + verify Redis
make db-demo       # Run persistence demo
make db-test       # Run database integration tests
make docker-db-only # Start only databases (no services)
```

**Fallback**: System runs in-memory mode when database URLs not set.

## Testing

```bash
make test              # All tests
make test-unit         # Unit tests
make test-integration  # API + database tests
make test-e2e          # Full-stack Docker tests (40+ scenarios)
```

See `tests/README.md` for details.

## Project Structure

```
coordinator/       # Coordinator service
├── api/          # REST endpoints
├── core/         # State manager, scheduler, workflow engine
├── db/           # PostgreSQL + Redis clients
└── utils/        # YAML parser

worker/           # Worker service
└── jobs/         # Job type implementations

shared/           # Common models, enums, messages
client/           # Python SDK
tests/
├── unit/         # Component tests
├── integration/  # API + DB tests
└── e2e/          # Full-stack Docker tests

examples/
└── workflow_definitions/  # Example YAML workflows
```

## Development

```bash
make help          # Show all commands
make lint          # Run linters
make clean         # Clean build artifacts
make reinstall     # Fresh install
```

## Documentation

- **QUICKSTART.md**: Step-by-step getting started
- **ARCHITECTURE.md**: System design and components
- **tests/README.md**: Testing infrastructure
- **examples/README.md**: Example usage patterns

