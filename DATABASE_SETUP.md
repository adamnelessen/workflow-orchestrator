# Database Integration

## Overview

The workflow orchestrator now supports **PostgreSQL** for persistent storage and **Redis** for caching and distributed coordination.

## Features

### PostgreSQL
- **Persistent storage** for workflows, jobs, and workers
- **Audit trail** of all workflow executions
- **Recovery** from coordinator restarts
- **Complex queries** for analytics

### Redis
- **Fast caching** layer for hot data
- **Distributed job queue** (replaces in-memory asyncio.Queue)
- **Worker presence** detection with TTL
- **Distributed locks** for coordination
- **Real-time metrics** tracking

## Quick Start

### Option 1: Using Make (Recommended)

```bash
# One command to set everything up
make db-init

# Or run the demo to see it in action
make db-demo

# Or start the full system
make docker-up
```

### Option 2: Using Docker Compose

```bash
docker-compose up
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- Coordinator (connected to both)
- 4 Workers

### Option 3: Manual Setup

```bash
# Start databases only
make docker-db-only

# Initialize schema
python scripts/init_db.py

# Run coordinator
export DATABASE_URL=postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator
export REDIS_URL=redis://localhost:6379/0
python -m coordinator.main
```

### Verify Databases

```bash
# Check PostgreSQL
docker-compose exec postgres psql -U workflow -d workflow_orchestrator -c "\dt"

# Check Redis
docker-compose exec redis redis-cli ping
```

### Run Without Databases (Development)

```bash
# Unset environment variables
unset DATABASE_URL
unset REDIS_URL

# Run coordinator
python -m coordinator.main
```

The system falls back to in-memory storage when DB URLs are not provided.

## Architecture

### Hybrid StateManager

The `StateManager` now supports three modes:

1. **In-memory only** (original behavior)
2. **With PostgreSQL** (persistence)
3. **With PostgreSQL + Redis** (persistence + performance)

### Data Flow

```
Write: Memory → Redis (cache) → PostgreSQL (persist)
Read:  Memory → Redis (if miss) → PostgreSQL (if miss)
```

### Backward Compatibility

All existing code continues to work! The StateManager provides synchronous methods that operate on in-memory state:

```python
# Synchronous (existing code)
workflow = state.get_workflow(workflow_id)
state.add_workflow(workflow)

# Asynchronous (new code with DB persistence)
workflow = await state.get_workflow_async(workflow_id)
await state.add_workflow_async(workflow)
```

## Database Schema

### Tables

- `workflows` - Workflow definitions and execution state
- `jobs` - Individual job records
- `workers` - Worker registry
- `job_assignments` - Job-to-worker mappings

### Redis Keys

- `queue:pending_jobs` - Job queue (sorted set by priority)
- `set:active_workers` - Live worker set
- `worker:heartbeat:{id}` - Worker presence (TTL 30s)
- `cache:workflows` - Workflow cache (hash)
- `cache:jobs` - Job cache (hash)
- `lock:{key}` - Distributed locks

## Configuration

### Environment Variables

```bash
# PostgreSQL
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0
```

### Docker Compose (Production)

```yaml
environment:
  - DATABASE_URL=postgresql+psycopg://workflow:workflow_prod@postgres:5432/workflow_orchestrator
  - REDIS_URL=redis://redis:6379/0
```

## Benefits

### Before (In-Memory)
❌ State lost on restart
❌ Single coordinator only
❌ No audit history
❌ Race conditions possible

### After (PostgreSQL + Redis)
✅ Full persistence and recovery
✅ Horizontal scaling ready
✅ Complete audit trail
✅ Distributed coordination
✅ High performance caching
✅ Worker presence detection

## Migration

### Existing Code

No changes required! The system is **100% backward compatible**.

### New Features

To leverage persistence:

```python
# Use async methods for DB operations
await state.add_workflow_async(workflow)

# Or use background task to persist sync operations
asyncio.create_task(state.add_workflow_async(workflow))
```

## Performance

- **Memory**: Fast (no change)
- **Redis**: ~0.1-1ms latency
- **PostgreSQL**: ~1-10ms latency

The hybrid approach keeps hot data in memory/Redis while PostgreSQL ensures persistence.

## Monitoring

### Health Checks

```bash
# PostgreSQL
curl http://localhost:8000/health

# Redis
docker-compose exec redis redis-cli INFO stats
```

### Metrics (via Redis)

```python
await redis.increment_metric("workflows_started")
count = await redis.get_metric("workflows_started")
```

## Next Steps

1. ✅ **Done**: Basic infrastructure
2. 🚀 **Next**: Migrate workflow engine to async persistence
3. 🚀 **Next**: Add database migrations (Alembic)
4. 🚀 **Next**: Implement Redis pub/sub for events
5. 🚀 **Next**: Add analytics endpoints
