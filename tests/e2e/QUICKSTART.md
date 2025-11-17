# E2E Testing Quick Reference

## Prerequisites
- Docker and docker-compose installed
- Virtual environment activated: `source .venv/bin/activate`
- Dependencies installed: `make install-dev`

## Quick Commands

### Run All E2E Tests
```bash
make test-e2e
```

### Manual Environment Management
```bash
# Start E2E environment
make test-e2e-up

# Check services are running
docker-compose -f tests/e2e/docker-compose.e2e.yml ps

# View logs
make test-e2e-logs

# Run tests against running environment
pytest tests/e2e/ -v -m e2e -s

# Stop environment
make test-e2e-down
```

### Run Specific Tests
```bash
# Single test file
pytest tests/e2e/test_workflow_lifecycle.py -v -s

# Single test class
pytest tests/e2e/test_worker_management.py::TestWorkerManagement -v -s

# Single test method
pytest tests/e2e/test_workflow_lifecycle.py::TestWorkflowLifecycle::test_data_processing_pipeline -v -s

# Specific keyword
pytest tests/e2e/ -k "parallel" -v -s
```

## Troubleshooting

### Problem: Containers won't start
```bash
# Solution: Clean up and rebuild
make test-e2e-down
docker system prune -f
make test-e2e-up
```

### Problem: Tests timeout
```bash
# Solution: Check logs for errors
make test-e2e-logs

# Or check specific service
docker-compose -f tests/e2e/docker-compose.e2e.yml logs coordinator-e2e
docker-compose -f tests/e2e/docker-compose.e2e.yml logs worker-e2e-1
```

### Problem: Port 8001 already in use
```bash
# Solution: Find and stop conflicting process
lsof -i :8001
# Or change port in tests/e2e/docker-compose.e2e.yml and conftest.py
```

### Problem: Workers don't connect
```bash
# Solution: Check health and connections
curl http://localhost:8001/health
curl http://localhost:8001/workers
```

## Test Output

### Successful Test
```
🐳 Starting E2E test environment...
⏳ Waiting for coordinator at http://localhost:8001...
✓ Coordinator is healthy
✓ E2E test environment ready

test_workflow_lifecycle.py::TestWorkflowLifecycle::test_data_processing_pipeline 
⏳ Waiting for at least 4 workers...
✓ 4 workers connected
📋 Submitted workflow: wf-abc123
  Workflow wf-abc123: PENDING
  Workflow wf-abc123: RUNNING
  Workflow wf-abc123: COMPLETED
✓ Workflow wf-abc123 completed successfully
PASSED
```

### Failed Test
```
test_workflow_lifecycle.py::TestWorkflowLifecycle::test_data_processing_pipeline 
⏳ Waiting for at least 4 workers...
✓ 4 workers connected
📋 Submitted workflow: wf-abc123
  Workflow wf-abc123: PENDING
  Workflow wf-abc123: RUNNING
TimeoutError: Workflow wf-abc123 did not reach COMPLETED within 30 seconds
FAILED
```

## Test Markers

Run tests by marker:
```bash
# Only E2E tests
pytest -m e2e -v

# E2E but not slow tests
pytest -m "e2e and not slow" -v

# All integration and E2E tests
pytest -m "integration or e2e" -v
```

## Debugging Tips

### 1. Run tests with output
```bash
pytest tests/e2e/ -v -s  # -s shows print statements
```

### 2. Keep environment running after failure
```bash
# Edit conftest.py docker_compose_e2e fixture to not teardown
# Or manually:
make test-e2e-up
pytest tests/e2e/test_workflow_lifecycle.py::test_data_processing_pipeline -v -s
# Don't run make test-e2e-down - inspect containers manually
```

### 3. Interactive debugging
```bash
# Add breakpoint in test
import pdb; pdb.set_trace()

# Run single test
pytest tests/e2e/test_workflow_lifecycle.py::test_data_processing_pipeline -v -s
```

### 4. Check coordinator API directly
```bash
# While environment is running
curl http://localhost:8001/health
curl http://localhost:8001/workers
curl http://localhost:8001/workflows

# Submit test workflow manually
curl -X POST http://localhost:8001/workflows/from-yaml \
  -H "Content-Type: text/plain" \
  --data-binary @examples/workflow_definitions/data-processing-pipeline.yaml
```

## Performance

Expected execution times:
- Environment startup: 10-20 seconds
- Single workflow test: 5-15 seconds
- Worker failure test: 20-40 seconds
- Full suite: 3-5 minutes

## CI/CD

### Local validation before push
```bash
# Run fast tests first
make test-unit
make test-integration

# Run E2E tests
make test-e2e

# All tests with coverage
pytest tests/ --cov=. --cov-report=term
```

### GitHub Actions example
```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run E2E tests
        run: make test-e2e
        timeout-minutes: 10
```

## Common Test Patterns

### Wait for workflow completion
```python
workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
final = workflow_waiter(e2e_client, workflow.id, timeout=30)
assert final["status"] == WorkflowStatus.COMPLETED
```

### Test worker failure
```python
workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
time.sleep(2)  # Let it start
stop_worker("worker-e2e-1")
final = workflow_waiter(e2e_client, workflow.id, timeout=60)
start_worker("worker-e2e-1")  # Clean up
```

### Test concurrent workflows
```python
workflows = []
for yaml_file in ["wf1.yaml", "wf2.yaml", "wf3.yaml"]:
    wf = e2e_client.submit_and_start_workflow(yaml_file)
    workflows.append(wf)

for wf in workflows:
    workflow_waiter(e2e_client, wf.id, timeout=60)
```

## Getting Help

1. Check test logs: `make test-e2e-logs`
2. Review E2E README: `tests/e2e/README.md`
3. Check test documentation: `tests/README.md`
4. Examine test fixtures: `tests/e2e/conftest.py`
