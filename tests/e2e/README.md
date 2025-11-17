# End-to-End (E2E) Tests

This directory contains end-to-end tests that validate the complete workflow orchestrator system by running real Docker containers.

## Overview

E2E tests spin up an isolated environment with:
- 1 Coordinator service
- 4 Worker services
- Real WebSocket connections
- Actual job processing

These tests validate the system as a whole, catching integration issues that unit and integration tests might miss.

## Quick Start

```bash
# Run all E2E tests (handles Docker automatically)
make test-e2e

# Start environment manually for debugging
make test-e2e-up
make test-e2e-logs

# Run specific test file
pytest tests/e2e/test_workflow_lifecycle.py -v -m e2e -s

# Clean up
make test-e2e-down
```

## Test Files

### `test_workflow_lifecycle.py`
Tests complete workflow execution from submission to completion:
- ✅ All three example workflows (data-processing, deployment, parallel-processing)
- ✅ Workflow status transitions
- ✅ Workflow cancellation
- ✅ Retrieving workflow details
- ✅ Listing workflows

### `test_worker_management.py`
Tests worker behavior and resilience:
- ✅ Worker connection on startup
- ✅ Worker capabilities verification
- ✅ Worker failure during workflow execution
- ✅ Worker reconnection
- ✅ Load distribution across workers
- ✅ Multiple worker failures

### `test_parallel_execution.py`
Tests concurrent execution and performance:
- ✅ Multiple concurrent workflows
- ✅ Workflow isolation
- ✅ High concurrency stress testing
- ✅ Parallel jobs within workflow
- ✅ Throughput measurement
- ✅ Sequential vs parallel performance

### `test_failure_scenarios.py`
Tests edge cases and error handling:
- ✅ Invalid YAML workflows
- ✅ Nonexistent files
- ✅ Nonexistent workflows
- ✅ Double-start workflows
- ✅ No workers available
- ✅ Rapid workflow submission
- ✅ Concurrent operations
- ✅ Health check under load

## Architecture

### Docker Compose Setup
```yaml
# tests/e2e/docker-compose.e2e.yml
coordinator-e2e:8001 → coordinator:8000
  ↓ WebSocket
worker-e2e-1 ─┐
worker-e2e-2 ─┤ Connected to coordinator
worker-e2e-3 ─┤ All capabilities enabled
worker-e2e-4 ─┘
```

### Isolated Environment
- Runs on port **8001** (dev environment uses 8000)
- Separate containers with `-e2e` suffix
- Independent from local development
- Clean state for each test session

## Fixtures

### Session-Level
- `docker_compose_e2e` - Manages Docker environment lifecycle
- `coordinator_url` - Coordinator URL (`http://localhost:8001`)

### Test-Level
- `e2e_client` - Pre-configured WorkflowClient
- `wait_for_workers` - Ensures minimum workers connected
- `workflow_waiter` - Helper to wait for workflow completion
- `workflow_definitions_path` - Path to example YAML files

### Helpers
- `stop_worker(worker_id)` - Stop a worker container
- `start_worker(worker_id)` - Start a worker container
- `get_container_logs(service_name)` - Retrieve container logs

## Writing E2E Tests

### Basic Pattern
```python
@pytest.mark.e2e
class TestMyScenario:
    def test_scenario(
        self,
        e2e_client: WorkflowClient,
        wait_for_workers,
        workflow_waiter,
        workflow_definitions_path
    ):
        # 1. Ensure workers are ready
        wait_for_workers
        
        # 2. Submit and start workflow
        yaml_path = workflow_definitions_path / "my-workflow.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
        
        # 3. Wait for completion
        final = workflow_waiter(e2e_client, workflow.id, timeout=30)
        
        # 4. Verify results
        assert final["status"] == WorkflowStatus.COMPLETED
```

### Testing Worker Failures
```python
def test_worker_failure(
    self,
    e2e_client,
    wait_for_workers,
    stop_worker,
    start_worker
):
    wait_for_workers
    
    # Stop a worker mid-execution
    stop_worker("worker-e2e-1")
    
    # Verify system continues working
    # ...
    
    # Clean up
    start_worker("worker-e2e-1")
```

## Best Practices

### ✅ Do
- Use `wait_for_workers` before starting workflows
- Set appropriate timeouts (workflows may be slow)
- Use `-s` flag to see progress output
- Clean up workers you stop in tests
- Test realistic scenarios

### ❌ Don't
- Run E2E tests in parallel (uses shared Docker environment)
- Hardcode timing assumptions (use polling)
- Leave containers running after failures
- Test internal implementation details (test behavior)

## Debugging

### View logs during test
```bash
# Terminal 1: Watch logs
make test-e2e-logs

# Terminal 2: Run tests
pytest tests/e2e/test_workflow_lifecycle.py::test_data_processing_pipeline -v -s
```

### Inspect running environment
```bash
# Start environment
make test-e2e-up

# Check services
docker-compose -f tests/e2e/docker-compose.e2e.yml ps

# Check specific service
docker-compose -f tests/e2e/docker-compose.e2e.yml logs coordinator-e2e

# Access coordinator API
curl http://localhost:8001/health
curl http://localhost:8001/workers
```

### Common Issues

**Containers won't start:**
```bash
make test-e2e-down
docker system prune -f
make test-e2e-up
```

**Tests timeout:**
- Check `make test-e2e-logs` for errors
- Increase timeout in `workflow_waiter` calls
- Verify system has enough resources

**Workers don't connect:**
- Check WebSocket URL in docker-compose.e2e.yml
- Verify health checks pass
- Review coordinator logs for connection errors

## Performance Expectations

Typical test run times:
- Single workflow test: 5-15 seconds
- Worker failure test: 20-40 seconds
- Stress test (5 concurrent workflows): 30-60 seconds
- Full E2E suite: 3-5 minutes

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run E2E tests
  run: |
    make test-e2e
  timeout-minutes: 10
```

### GitLab CI
```yaml
e2e-tests:
  stage: test
  services:
    - docker:dind
  script:
    - make test-e2e
  timeout: 10m
```

## Maintenance

### Adding New E2E Tests
1. Create test in appropriate file (or new file)
2. Mark with `@pytest.mark.e2e`
3. Use existing fixtures
4. Document the scenario being tested
5. Ensure cleanup happens

### Updating Docker Environment
Edit `docker-compose.e2e.yml`:
- Add more workers if needed
- Adjust environment variables
- Update health check timings
- Modify resource limits

## Coverage

E2E tests complement unit and integration tests:

| Test Type | Speed | Scope | Coverage |
|-----------|-------|-------|----------|
| Unit | Fast | Single components | Internal logic |
| Integration | Medium | API endpoints | API contracts |
| **E2E** | **Slow** | **Full system** | **Real workflows** |

Run all test types for comprehensive coverage:
```bash
make test-unit        # Quick feedback
make test-integration # API validation
make test-e2e        # System validation
```
