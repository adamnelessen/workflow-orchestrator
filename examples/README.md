# Workflow Examples

This directory contains example workflow definitions and scripts demonstrating how to use the Workflow Orchestrator client.

## Workflow Definitions

The `workflow_definitions/` directory contains sample YAML workflow definitions:

- **simple-workflow.yaml** - A basic two-step workflow with validation and processing
- **data-processing-pipeline.yaml** - A more complex data processing workflow
- **deployment-pipeline.yaml** - An example deployment workflow

## Example Scripts

### submit_workflow.py

Demonstrates how to submit a single workflow from a YAML file and monitor its execution.

```bash
# Make sure the coordinator and workers are running first
make submit-workflow
```

This script:
1. Submits the `simple-workflow.yaml` definition to the coordinator
2. Starts the workflow immediately
3. Monitors the workflow execution status
4. Displays job completion details

### workflow_demo.py

A comprehensive demonstration of workflow client operations.

```bash
make workflow-demo
```

This script:
1. Checks coordinator connectivity
2. Submits all workflow definitions from `workflow_definitions/`
3. Lists all workflows in the system
4. Starts a specific workflow by name
5. Monitors workflow execution

## Using the Client Programmatically

```python
from client.workflow_client import WorkflowClient

# Initialize client
client = WorkflowClient(base_url="http://localhost:8000")

# Submit a workflow from YAML
workflow = client.submit_workflow_from_yaml("path/to/workflow.yaml")

# Start the workflow
client.start_workflow(workflow.id)

# Monitor workflow status
workflow = client.get_workflow(workflow.id)
print(f"Status: {workflow.status}")

# Or do both in one step
workflow = client.submit_and_start_workflow("path/to/workflow.yaml")
```

## Available Client Methods

- `get_workers()` - List connected workers
- `submit_workflow_from_yaml(yaml_path)` - Submit a workflow from a YAML file
- `start_workflow(workflow_id)` - Start a workflow execution
- `submit_and_start_workflow(yaml_path)` - Submit and start in one operation
- `get_workflow(workflow_id)` - Get workflow details and status
- `list_workflows()` - List all workflows
- `cancel_workflow(workflow_id)` - Cancel a running workflow
- `delete_workflow(workflow_id)` - Delete a workflow

## Prerequisites

Before running the examples:

1. Start the coordinator:
   ```bash
   make run-coordinator
   ```

2. Start one or more workers:
   ```bash
   make run-worker
   ```

3. Ensure all dependencies are installed:
   ```bash
   pip install -e .
   ```
