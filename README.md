# Workflow Orchestrator

A distributed workflow orchestration system with coordinator and worker components.

## 🚀 Quick Start

**New here?** Check out [QUICKSTART.md](QUICKSTART.md) for a step-by-step guide!

```bash
# One command to get started
make help

# Setup with databases (recommended)
make db-init

# Or use the classic setup script
./setup.sh
```

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
# Build containers (includes PostgreSQL + Redis)
make docker-build

# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

## Database Support

The orchestrator now supports **PostgreSQL** for persistence and **Redis** for caching:

- **PostgreSQL**: Persistent storage for workflows, jobs, and workers
- **Redis**: Fast caching, job queues, and distributed coordination

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed configuration.

### Quick Start with Databases

```bash
# Option 1: One-command setup (recommended)
make db-init

# Option 2: Run the demo to see persistence in action
make db-demo

# Option 3: Start everything (coordinator + workers + databases)
make docker-up
```

### Database Commands

```bash
# Start only PostgreSQL + Redis (without coordinator/workers)
make docker-db-only

# Initialize database schema
make db-init

# Run database persistence demo
make db-demo

# Run database-specific tests
make db-test
```

### Manual Database Setup

If you prefer manual setup:

```bash
# Install dependencies
pip install -e .

# Start databases
docker-compose up -d postgres redis

# Initialize PostgreSQL schema and verify Redis
python scripts/init_db.py

# Run coordinator with databases
export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0
python -m coordinator.main
```

### Run Without Databases

The system falls back to in-memory storage when database URLs are not set:

```bash
# No DATABASE_URL or REDIS_URL needed
python -m coordinator.main
```

## Project Structure

```
workflow-orchestrator/
├── coordinator/       # Coordinator service
├── worker/           # Worker service
├── shared/           # Shared schemas and utilities
├── tests/            # Test files
├── examples/         # Example workflows
└── docker/           # Docker configurations
```

## Workflow Definitions

### YAML Format

Workflows can be defined using YAML files with the following structure:

```yaml
workflow:
  name: "data-processing-pipeline"
  jobs:
    - id: "validate-input"
      type: "validation"
      parameters:
        schema: "user-data"
      on_success: "process-data"
      on_failure: "send-error-notification"
    
    - id: "process-data"
      type: "processing"
      parameters:
        operation: "transform"
      on_success: "save-results"
      on_failure: "cleanup-temp-files"
    
    - id: "save-results"
      type: "integration"
      parameters:
        endpoint: "data-store"
    
    - id: "send-error-notification"
      type: "integration"
      parameters:
        recipient: "admin@company.com"
    
    - id: "cleanup-temp-files"
      type: "cleanup"
      parameters:
        target: "temp-files"
      always_run: true
```

### Field Reference

**Workflow fields:**
- `name` (required): Human-readable workflow name

**Job fields:**
- `id` (required): Unique job identifier
- `type` (required): Job type - one of: `validation`, `processing`, `integration`, `cleanup`
- `parameters` (optional): Dictionary of job-specific parameters
- `on_success` (optional): Job ID to run if this job succeeds
- `on_failure` (optional): Job ID to run if this job fails
- `always_run` (optional, default: false): Run this job regardless of workflow state
- `max_retries` (optional, default: 3): Maximum number of retry attempts

### Control Flow

Jobs support conditional execution through `on_success` and `on_failure` fields:
- When a job completes successfully, the job specified in `on_success` is triggered
- When a job fails, the job specified in `on_failure` is triggered
- Jobs with `always_run: true` will execute even if the workflow has failed jobs

### Loading Workflows

**Via API:**
```bash
curl -X POST http://localhost:8000/workflows/from-yaml \
  -H "Content-Type: text/plain" \
  --data-binary @examples/workflow_definitions/data-processing-pipeline.yaml
```

**Example workflows** are available in `examples/workflow_definitions/`:
- `data-processing-pipeline.yaml` - Data validation and processing with error handling
- `deployment-pipeline.yaml` - Multi-stage deployment with rollback
- `simple-workflow.yaml` - Basic sequential workflow

