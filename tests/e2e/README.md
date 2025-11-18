# End-to-End Tests

Full-stack validation with real Docker containers (40+ tests).

## Quick Start

```bash
make test-e2e          # Run all E2E tests
make test-e2e-up       # Start environment
make test-e2e-logs     # View logs
make test-e2e-down     # Stop environment
```

## Overview

E2E tests validate the complete system:
- 1 coordinator + 4 workers (isolated on port 8001)
- Real WebSocket connections
- Actual job processing
- Full integration validation

## Test Suites

### test_workflow_lifecycle.py (8 tests)
Complete workflow execution from submission to completion:
- Example workflow execution (data-processing, deployment, parallel-processing)
- Status transitions
- Workflow cancellation
- List and retrieve operations

### test_worker_management.py (9 tests)
Worker resilience and load distribution:
- Worker connections on startup
- Capability verification
- Worker failure during execution
- Worker reconnection
- Load distribution across pool
- Multiple simultaneous failures

### test_parallel_execution.py (7 tests)
Concurrent execution and performance:
- Multiple concurrent workflows
- Workflow isolation
- High concurrency stress testing
- Parallel jobs within workflows
- Throughput measurement

### test_failure_scenarios.py (13+ tests)
Edge cases and error handling:
- Invalid YAML rejection
- Nonexistent files and workflows
- Double-start prevention
- No workers available
- Rapid workflow submission
- Concurrent operations
- Health check under load

## Architecture

```
Tests (Python) → http://localhost:8001
                       ↓
                 coordinator-e2e
                       ↓
         ┌─────────────┴─────────────┐
    worker-e2e-1  worker-e2e-2  worker-e2e-3  worker-e2e-4
```

Isolated from development environment (port 8000).

## Fixtures

**Session-level**:
- `docker_compose_e2e`: Manages Docker lifecycle
- `coordinator_url`: Returns `http://localhost:8001`

**Test-level**:
- `e2e_client`: Pre-configured WorkflowClient
- `wait_for_workers`: Ensures minimum workers connected
- `workflow_waiter`: Helper for workflow completion polling
- `workflow_definitions_path`: Path to example YAML files
- `stop_worker(id)` / `start_worker(id)`: Control worker containers

## Running Tests

```bash
# All E2E tests
pytest tests/e2e/ -v -m e2e

# Specific test file
pytest tests/e2e/test_workflow_lifecycle.py -v -s

# Specific test
pytest tests/e2e/test_workflow_lifecycle.py::TestWorkflowLifecycle::test_data_processing_pipeline -v -s

# By keyword
pytest tests/e2e/ -k "parallel" -v -s
```

## Writing E2E Tests

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
        # 1. Ensure workers ready
        wait_for_workers
        
        # 2. Submit and start workflow
        yaml_path = workflow_definitions_path / "my-workflow.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
        
        # 3. Wait for completion
        final = workflow_waiter(e2e_client, workflow.id, timeout=30)
        
        # 4. Verify
        assert final["status"] == WorkflowStatus.COMPLETED
```

## Debugging

```bash
# Start environment manually
make test-e2e-up

# Check services
docker-compose -f tests/e2e/docker-compose.e2e.yml ps

# View logs
make test-e2e-logs

# Test coordinator API
curl http://localhost:8001/health
curl http://localhost:8001/workers

# Run specific test
pytest tests/e2e/test_workflow_lifecycle.py::test_data_processing_pipeline -v -s

# Clean up
make test-e2e-down
```

## Troubleshooting

**Containers won't start:**
```bash
make test-e2e-down
docker system prune -f
make test-e2e-up
```

**Tests timeout:**
- Check logs: `make test-e2e-logs`
- Increase timeout in `workflow_waiter` calls
- Verify system resources

**Workers don't connect:**
- Check WebSocket URL in `docker-compose.e2e.yml`
- Review coordinator logs for connection errors
- Verify health: `curl http://localhost:8001/health`

## Performance

Typical execution times:
- Single workflow test: 5-15s
- Worker failure test: 20-40s
- Stress test (5 workflows): 30-60s
- Full suite: 3-5 minutes

## CI/CD Integration

```yaml
# GitHub Actions
- name: Run E2E tests
  run: make test-e2e
  timeout-minutes: 10
```
