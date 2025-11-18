# Database Integration Tests

Comprehensive PostgreSQL and Redis integration testing.

## Test Files

**`test_postgres_integration.py`**: PostgreSQL CRUD operations for workflows, jobs, workers, and job assignments

**`test_redis_integration.py`**: Redis caching, job queues, worker heartbeats, distributed locks, metrics

**`test_state_manager_persistence.py`**: Full-stack StateManager with three-tier caching, cache rebuild after restart, data consistency

## Running Tests

### Prerequisites

```bash
# Start databases
docker-compose up -d postgres redis

# Set environment variables
export DATABASE_URL="postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator_test"
export REDIS_URL="redis://localhost:6379/1"
```

### Run Tests

```bash
# All integration tests
pytest tests/integration/ -v

# Specific file
pytest tests/integration/test_postgres_integration.py -v
pytest tests/integration/test_redis_integration.py -v
pytest tests/integration/test_state_manager_persistence.py -v

# With coverage
pytest tests/integration/ --cov=coordinator --cov-report=html
```

**Auto-skip**: Tests automatically skip if `DATABASE_URL` or `REDIS_URL` not set.

## Coverage

### PostgreSQL
- Workflow CRUD and status updates
- Job CRUD, status, and worker assignments
- Worker CRUD and listing
- Job assignment tracking
- Data persistence and retrieval

### Redis
- Workflow/job caching and invalidation
- Priority-based job queue (push/pop)
- Worker heartbeat with TTL
- Active/inactive worker tracking
- Distributed locks (acquire/release)
- Metric counters
- Cache miss handling

### StateManager Persistence
- Three-tier caching (memory → Redis → PostgreSQL)
- **Cache rebuild after coordinator restart** (critical resilience test)
- Data consistency across storage layers
- Cascading deletes
- End-to-end persistence workflows

## Key Test: Cache Rebuild

`test_rebuild_from_db_after_restart()` validates:
1. Data persisted to PostgreSQL
2. StateManager instance closed (simulates crash)
3. New StateManager starts fresh
4. `init_state_manager()` calls `_rebuild_from_db()`
5. All workflows/workers/assignments restored to memory
6. System immediately operational

Ensures **zero data loss** and **fast recovery**.

## Troubleshooting

**Tests skipped**: Verify `DATABASE_URL` and `REDIS_URL` are set and databases are running

**Connection errors**: Check connection strings, verify PostgreSQL uses `psycopg` driver

**Test isolation**: Use separate database/Redis index for tests (e.g., Redis index 1)

## CI/CD Integration

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_DB: workflow_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
  redis:
    image: redis:7

env:
  DATABASE_URL: postgresql+psycopg://test:test@postgres:5432/workflow_test
  REDIS_URL: redis://redis:6379/0

run: pytest tests/integration/ -v
```
