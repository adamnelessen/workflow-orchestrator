# Workflow Examples

Example workflows and Python client usage demonstrating the orchestrator's capabilities.

## Workflow Definitions

Located in `workflow_definitions/`:

- **data-processing-pipeline.yaml**: Multi-stage data pipeline with validation, transformation, and error handling
- **deployment-pipeline.yaml**: Deployment workflow with rollback capabilities
- **parallel-processing.yaml**: Concurrent job execution example

## Python Scripts

### submit_workflow.py

Submit and monitor a single workflow:

```bash
make submit-workflow
# Or manually:
python examples/submit_workflow.py examples/workflow_definitions/data-processing-pipeline.yaml
```

### workflow_demo.py

Comprehensive client API demonstration:

```bash
make workflow-demo
```

Features:
- Health checks
- Bulk workflow submission
- Workflow listing
- Status monitoring
- Start/cancel operations

## Client Usage

```python
from client.workflow_client import WorkflowClient

client = WorkflowClient("http://localhost:8000")

# Submit from YAML
workflow = client.submit_workflow_from_yaml("workflow.yaml")

# Start execution
client.start_workflow(workflow.id)

# Monitor status
status = client.get_workflow(workflow.id)
print(f"Status: {status.status}")

# Or combine operations
workflow = client.submit_and_start_workflow("workflow.yaml")
```

## Client Methods

- `get_workers()`: List connected workers
- `submit_workflow_from_yaml(path)`: Parse and submit YAML workflow
- `start_workflow(workflow_id)`: Start workflow execution
- `submit_and_start_workflow(path)`: Submit + start in one call
- `get_workflow(workflow_id)`: Get workflow details
- `list_workflows()`: List all workflows
- `cancel_workflow(workflow_id)`: Cancel running workflow
- `delete_workflow(workflow_id)`: Delete workflow

## Prerequisites

Ensure coordinator and workers are running:

```bash
# Docker (recommended)
make docker-up

# Or locally
make install
make docker-db-only
python -m coordinator.main  # Terminal 1
python -m worker.main       # Terminal 2
```
