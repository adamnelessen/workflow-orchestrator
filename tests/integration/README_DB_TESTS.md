# Database Integration Tests

This directory contains comprehensive integration tests for PostgreSQL and Redis.

## Test Files

### `test_postgres_integration.py`
Tests PostgreSQL database operations:
- Workflow CRUD operations
- Job CRUD operations
- Worker CRUD operations
- Job assignment tracking
- Data persistence and retrieval

### `test_redis_integration.py`
Tests Redis caching operations:
- Workflow and job caching
- Cache invalidation
- Job queue operations (push/pop with priority)
- Worker heartbeat tracking
- Distributed locks
- Metrics tracking

### `test_state_manager_persistence.py`
Tests full-stack StateManager with both databases:
- Three-tier caching (memory → Redis → PostgreSQL)
- Cache rebuild after coordinator restart
- Data consistency across all storage layers
- Cascading deletes
- End-to-end persistence workflows

## Running the Tests

### Prerequisites

1. **PostgreSQL** must be running and accessible
2. **Redis** must be running and accessible
3. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator_test"
   export REDIS_URL="redis://localhost:6379/1"
   ```

### Using Docker Compose (Recommended)

Start test databases:
```bash
docker-compose up -d postgres redis
```

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_postgres_integration.py -v
pytest tests/integration/test_redis_integration.py -v
pytest tests/integration/test_state_manager_persistence.py -v

# Run with coverage
pytest tests/integration/ -v --cov=coordinator --cov-report=html
```

### Run Without Databases

If databases are not available, tests will be **automatically skipped** with a clear message:
```
SKIPPED [1] tests/integration/test_postgres_integration.py:11: DATABASE_URL not set - skipping PostgreSQL tests
```

## Test Coverage

### PostgreSQL Tests Coverage
- ✅ Save and retrieve workflows
- ✅ Update workflow status
- ✅ List all workflows
- ✅ Delete workflows
- ✅ Save and retrieve jobs
- ✅ Update job status and assignments
- ✅ Save and retrieve workers
- ✅ List all workers
- ✅ Delete workers
- ✅ Job assignment CRUD operations
- ✅ Multiple assignments tracking

### Redis Tests Coverage
- ✅ Cache workflow data
- ✅ Cache job data
- ✅ Cache invalidation
- ✅ Job queue with priority ordering
- ✅ Worker heartbeat with TTL expiration
- ✅ Worker active/inactive tracking
- ✅ Distributed lock acquire/release
- ✅ Metric counters
- ✅ Cache miss handling
- ✅ Empty queue handling

### StateManager Tests Coverage
- ✅ Workflow persistence to PostgreSQL
- ✅ Workflow caching in Redis
- ✅ Three-tier read path (memory → Redis → PostgreSQL)
- ✅ **Cache rebuild after restart** (critical resilience test)
- ✅ Worker persistence
- ✅ Job assignment persistence
- ✅ Cascading deletes across all layers
- ✅ List operations after restart
- ✅ Job update propagation

## Key Test: Cache Rebuild After Restart

The most critical test is `test_rebuild_from_db_after_restart()` which validates:

1. Data is persisted to PostgreSQL
2. First StateManager instance is closed (simulates crash)
3. New StateManager instance starts fresh
4. `init_state_manager()` automatically calls `_rebuild_from_db()`
5. All workflows, workers, and job assignments are restored to memory
6. System is immediately operational with full state

This ensures **zero data loss** and **fast recovery** after coordinator restarts.

## Troubleshooting

### Tests are skipped
- Check that `DATABASE_URL` and `REDIS_URL` environment variables are set
- Verify databases are running: `docker-compose ps`

### Connection errors
- Check database connection strings
- Ensure PostgreSQL is using `psycopg` driver: `postgresql+psycopg://...`
- Test Redis connection: `redis-cli ping`

### Test database isolation
- Use separate database/Redis index for tests (e.g., Redis index 1 instead of 0)
- Clean up test data between runs if needed

## CI/CD Integration

For automated testing in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
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
