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
└── integration/             # Integration tests for APIs and workflows
    ├── test_api_workflows.py
    ├── test_api_workers.py
    └── test_websocket.py
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

## CI/CD Integration

Add to your CI pipeline:
```bash
# Run tests with coverage
pytest --cov=. --cov-report=xml --cov-report=term

# Fail if coverage below threshold
pytest --cov=. --cov-fail-under=80
```

## Best Practices

1. **Use fixtures** - Don't create test data manually
2. **Mark tests appropriately** - Use `@pytest.mark.unit` and `@pytest.mark.integration`
3. **Test one thing** - Each test should verify one behavior
4. **Use descriptive names** - Test names should describe what they test
5. **Arrange-Act-Assert** - Structure tests with clear setup, execution, and verification
6. **Mock external dependencies** - Don't rely on external services in tests
7. **Clean up** - Fixtures should clean up resources after tests
