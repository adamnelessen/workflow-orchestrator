# Testing Infrastructure

This directory contains the test suite for the workflow orchestrator.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests for individual components
│   ├── test_state_manager.py
│   ├── test_scheduler.py
│   └── test_worker_registry.py
├── integration/             # Integration tests for APIs and workflows
│   ├── test_api_workflows.py
│   ├── test_api_workers.py
│   └── test_websocket.py
└── e2e/                     # End-to-end tests with Docker
    ├── conftest.py
    ├── docker-compose.e2e.yml
    ├── test_workflow_lifecycle.py
    ├── test_worker_management.py
    ├── test_parallel_execution.py
    └── test_failure_scenarios.py
```

## Running Tests

### Install dependencies
```bash
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run specific test types
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only (requires Docker)
pytest -m e2e

# Async tests
pytest -m asyncio

# Slow tests
pytest -m slow
```

### Run with coverage
```bash
pytest --cov=coordinator --cov=worker --cov=shared --cov=client
```

### Run specific test file
```bash
pytest tests/unit/test_scheduler.py
```

### Run specific test
```bash
pytest tests/unit/test_scheduler.py::TestScheduler::test_assign_job_success
```

### Verbose output
```bash
pytest -v
```

### Show print statements
```bash
pytest -s
```

## End-to-End (E2E) Tests

E2E tests validate the complete system by running actual Docker containers with coordinator and workers.

### Prerequisites
- Docker and docker-compose installed
- Sufficient system resources for running 5 containers (coordinator + 4 workers)

### Running E2E Tests

```bash
# Run all E2E tests (automatically manages Docker environment)
make test-e2e

# Or with pytest directly
pytest tests/e2e/ -v -m e2e -s

# Manually manage E2E environment for debugging
make test-e2e-up      # Start containers
make test-e2e-logs    # View logs
pytest tests/e2e/     # Run tests against running environment
make test-e2e-down    # Stop containers
```

### E2E Test Categories

1. **Workflow Lifecycle** (`test_workflow_lifecycle.py`)
   - Complete workflow execution
   - Status transitions
   - Workflow cancellation
   - Multiple workflow definitions

2. **Worker Management** (`test_worker_management.py`)
   - Worker connections/disconnections
   - Worker failure handling
   - Load distribution
   - Worker reconnection

3. **Parallel Execution** (`test_parallel_execution.py`)
   - Concurrent workflows
   - Workflow isolation
   - Throughput testing
   - Performance comparisons

4. **Failure Scenarios** (`test_failure_scenarios.py`)
   - Invalid workflows
   - Missing dependencies
   - System under load
   - Edge cases

### E2E Test Fixtures

- `docker_compose_e2e` - Session-scoped Docker environment
- `e2e_client` - WorkflowClient configured for E2E tests
- `wait_for_workers` - Ensures workers are connected
- `workflow_waiter` - Helper to wait for workflow completion
- `stop_worker` / `start_worker` - Control worker containers
- `get_container_logs` - Retrieve logs for debugging

### Test Environment

E2E tests use an isolated environment on port 8001:
- Coordinator: `http://localhost:8001`
- Workers: 4 workers (e2e-worker-1 through e2e-worker-4)
- Separate from development environment (port 8000)

## Test Fixtures

### Data Factories
- `job_factory()` - Create test Job instances
- `workflow_factory()` - Create test Workflow instances  
- `worker_factory()` - Create test Worker instances

### Component Fixtures
- `state_manager` - Fresh StateManager instance
- `populated_state` - StateManager with test data
- `mock_websocket` - Mock WebSocket connection
- `mock_worker_registry` - Mock WorkerRegistry

### Sample Data
- `sample_job_parameters` - Example parameters for different job types
- `sample_workflow_config` - Example workflow configuration

## Usage Examples

### Using fixtures in tests
```python
def test_something(workflow_factory, state_manager):
    # Create test workflow
    workflow = workflow_factory(workflow_id="test-1")
    
    # Use state manager
    state_manager.add_workflow(workflow)
    
    # Assert
    assert state_manager.get_workflow("test-1") == workflow
```

### Testing async code
```python
@pytest.mark.asyncio
async def test_async_operation(scheduler):
    result = await scheduler.assign_job("job-1", JobType.VALIDATION, {})
    assert result is not None
```

### Using markers
```python
@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.e2e
def test_end_to_end():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass
```

## Writing New Tests

### Unit Test Template
```python
import pytest

@pytest.mark.unit
class TestMyComponent:
    """Test MyComponent functionality"""
    
    def test_something(self, state_manager):
        # Arrange
        component = MyComponent(state_manager)
        
        # Act
        result = component.do_something()
        
        # Assert
        assert result == expected
```

### Integration Test Template
```python
import pytest
from fastapi.testclient import TestClient
from coordinator.main import app

@pytest.mark.integration
class TestMyEndpoint:
    """Test API endpoint"""
    
    def test_endpoint(self):
        client = TestClient(app)
        response = client.get("/my-endpoint")
        assert response.status_code == 200
```

### E2E Test Template
```python
import pytest
from client.workflow_client import WorkflowClient

@pytest.mark.e2e
class TestMyE2EScenario:
    """Test complete system scenario"""
    
    def test_scenario(
        self,
        e2e_client: WorkflowClient,
        wait_for_workers,
        workflow_waiter,
        workflow_definitions_path
    ):
        # Ensure workers ready
        wait_for_workers
        
        # Execute workflow
        yaml_path = workflow_definitions_path / "my-workflow.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
        
        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)
        
        # Verify
        assert final_workflow["status"] == WorkflowStatus.COMPLETED
```

## CI/CD Integration

Add to your CI pipeline:
```bash
# Run unit and integration tests
pytest tests/unit tests/integration --cov=. --cov-report=xml --cov-report=term

# Run E2E tests (requires Docker)
make test-e2e

# Fail if coverage below threshold
pytest --cov=. --cov-fail-under=80
```

### GitHub Actions Example
```yaml
- name: Run unit and integration tests
  run: pytest tests/unit tests/integration -v

- name: Run E2E tests
  run: make test-e2e
```

## Best Practices

1. **Use fixtures** - Don't create test data manually
2. **Mark tests appropriately** - Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
3. **Test one thing** - Each test should verify one behavior
4. **Use descriptive names** - Test names should describe what they test
5. **Arrange-Act-Assert** - Structure tests with clear setup, execution, and verification
6. **Mock external dependencies** - Don't rely on external services in unit/integration tests
7. **Clean up** - Fixtures should clean up resources after tests
8. **E2E for real scenarios** - Use E2E tests to validate complete workflows, not individual functions

## Troubleshooting E2E Tests

### Containers won't start
```bash
# Check Docker is running
docker ps

# Clean up old containers
make test-e2e-down
docker system prune -f

# Rebuild images
make test-e2e-up
```

### Tests timeout
- Increase timeout values in test fixtures
- Check container logs: `make test-e2e-logs`
- Ensure sufficient system resources

### Worker connection issues
- Verify health checks pass
- Check network connectivity between containers
- Review coordinator logs for WebSocket errors
