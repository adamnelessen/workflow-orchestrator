# Testing Infrastructure

Comprehensive test suite with unit, integration, and end-to-end tests.

## Structure

```
tests/
├── unit/          # Component tests (fast)
├── integration/   # API + database tests (medium)
└── e2e/           # Full-stack Docker tests (slow)
```

## Quick Start

```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-e2e          # E2E tests (requires Docker)
```

## Unit Tests

Fast, isolated component tests:

```bash
pytest tests/unit/ -v

# Specific component
pytest tests/unit/test_scheduler.py
pytest tests/unit/test_state_manager.py
```

**Coverage**: StateManager, Scheduler, WorkerRegistry, WorkflowEngine, workflow parsing.

## Integration Tests

API endpoints and database operations:

```bash
# Requires databases running
make docker-db-only

# Run integration tests
pytest tests/integration/ -v
```

**Test files**:
- `test_api_*.py`: REST endpoint validation
- `test_postgres_integration.py`: PostgreSQL CRUD operations
- `test_redis_integration.py`: Redis caching and queue operations
- `test_state_manager_persistence.py`: Full persistence stack

See [integration/README_DB_TESTS.md](integration/README_DB_TESTS.md) for database test details.

## End-to-End Tests

Full-stack validation with real Docker containers (40+ tests):

```bash
make test-e2e
```

Automatically manages:
- 1 coordinator container
- 4 worker containers
- Isolated environment on port 8001

**Test suites**:
- `test_workflow_lifecycle.py`: Complete workflow execution (8 tests)
- `test_worker_management.py`: Worker failures and recovery (9 tests)
- `test_parallel_execution.py`: Concurrent workflows (7 tests)
- `test_failure_scenarios.py`: Edge cases and errors (13+ tests)

See [e2e/README.md](e2e/README.md) and [e2e/QUICKSTART.md](e2e/QUICKSTART.md) for details.

### Manual E2E Environment

```bash
make test-e2e-up       # Start environment
make test-e2e-logs     # View logs
pytest tests/e2e/      # Run tests
make test-e2e-down     # Stop environment
```

## Test Markers

```bash
pytest -m unit         # Unit tests only
pytest -m integration  # Integration tests only
pytest -m e2e          # E2E tests only
pytest -m asyncio      # Async tests
pytest -m slow         # Slow tests
```

## Coverage

```bash
pytest --cov=coordinator --cov=worker --cov=shared --cov=client
pytest --cov=. --cov-report=html  # HTML report
```

## Fixtures

Common fixtures in `conftest.py`:

- **Factories**: `job_factory`, `workflow_factory`, `worker_factory`
- **Components**: `state_manager`, `scheduler`, `worker_registry`
- **Mocks**: `mock_websocket`, `mock_worker_registry`
- **E2E**: `e2e_client`, `wait_for_workers`, `workflow_waiter`

## Best Practices

1. **Mark tests appropriately**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
2. **Use fixtures**: Avoid manual test data creation
3. **AAA pattern**: Arrange-Act-Assert structure
4. **Descriptive names**: Test names should describe behavior
5. **Clean up**: Fixtures handle resource cleanup
6. **Mock externals**: Unit tests shouldn't touch databases/network

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    make test-unit
    make test-integration
    make test-e2e
```

## Troubleshooting

**E2E tests timeout:**
- Check logs: `make test-e2e-logs`
- Verify Docker resources
- Increase timeout values

**Database tests skipped:**
- Set `DATABASE_URL` and `REDIS_URL` environment variables
- Start databases: `make docker-db-only`

**Port conflicts:**
- E2E uses port 8001 (separate from dev on 8000)
- Check with: `lsof -i :8001`
