# Quick Start Guide

Get the workflow orchestrator running in under 2 minutes.

## One-Command Start

```bash
make quick-start
```

This command:
1. Installs dependencies
2. Starts coordinator + 4 workers + PostgreSQL + Redis
3. Submits example workflow

## What's Running

- **Coordinator**: `http://localhost:8000` - API server and job scheduler
- **Workers**: 4 parallel job processors
- **PostgreSQL**: Persistent workflow storage
- **Redis**: Cache and job queue

## View Activity

```bash
# Watch logs
make docker-logs

# Check health
curl http://localhost:8000/health

# List workers
curl http://localhost:8000/workers

# List workflows
curl http://localhost:8000/workflows
```

## Submit Another Workflow

```bash
# Default: data-processing-pipeline.yaml
make submit-workflow

# Specific workflow
make submit-workflow WORKFLOW=parallel-processing.yaml
make submit-workflow WORKFLOW=deployment-pipeline.yaml
```

## Stop Services

```bash
make docker-down
```

## Development Setup

Run coordinator and workers locally (outside Docker):

```bash
# Install dependencies
make install-dev

# Start only databases
make docker-db-only

# Terminal 1: Coordinator
export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0
python -m coordinator.main

# Terminal 2: Worker
export COORDINATOR_URL=ws://localhost:8000/workers
export WORKER_ID=local-worker-1
python -m worker.main
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make quick-start` | Start everything + submit demo |
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |
| `make docker-logs` | View logs |
| `make submit-workflow` | Submit example workflow |
| `make test` | Run test suite |
| `make help` | Show all commands |

## Troubleshooting

**Services won't start?**
```bash
make docker-down
docker system prune -f
make quick-start
```

**Port already in use?**
```bash
lsof -i :8000
kill -9 <PID>
```

**Fresh start?**
```bash
make clean
make quick-start
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check [examples/](examples/) for more workflows
- Run `make test-e2e` to see 40+ integration tests
