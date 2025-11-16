#!/usr/bin/env python3
"""Example script demonstrating advanced workflow client operations."""

import sys
import time
from pathlib import Path

from client.workflow_client import WorkflowClient


def submit_all_workflows(client: WorkflowClient):
    """Submit all workflow definitions in the workflow_definitions directory."""
    workflow_dir = Path(__file__).parent / "workflow_definitions"
    yaml_files = list(workflow_dir.glob("*.yaml"))

    print(f"Found {len(yaml_files)} workflow definitions")
    submitted_workflows = []

    for yaml_file in yaml_files:
        print(f"\nSubmitting: {yaml_file.name}")
        try:
            workflow = client.submit_workflow_from_yaml(str(yaml_file))
            print(f"  ✓ Submitted: {workflow.name} (ID: {workflow.id})")
            submitted_workflows.append(workflow)
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    return submitted_workflows


def list_all_workflows(client: WorkflowClient):
    """List all workflows in the system."""
    print("\n" + "=" * 60)
    print("All Workflows:")
    print("=" * 60)

    workflows = client.list_workflows()

    if not workflows:
        print("No workflows found")
        return

    for workflow in workflows:
        print(f"\n{workflow.name} (ID: {workflow.id})")
        print(f"  Status: {workflow.status}")
        print(f"  Jobs: {len(workflow.jobs)}")
        print(f"  Created: {workflow.created_at}")


def start_workflow_by_name(client: WorkflowClient, workflow_name: str):
    """Find and start a workflow by name."""
    workflows = client.list_workflows()

    for workflow in workflows:
        if workflow.name == workflow_name:
            print(f"\nStarting workflow: {workflow.name}")
            result = client.start_workflow(workflow.id)
            print(f"  ✓ {result['message']}")
            return workflow.id

    print(f"  ✗ Workflow '{workflow_name}' not found")
    return None


def main():
    """Demonstrate various workflow client operations."""
    # Initialize client
    client = WorkflowClient(base_url="http://localhost:8000")

    print("=" * 60)
    print("Workflow Client Demo")
    print("=" * 60)

    # Check if coordinator is running
    try:
        workers = client.get_workers()
        print(f"\n✓ Connected to coordinator")
        print(f"  Active workers: {len(workers)}")
    except Exception as e:
        print(f"\n✗ Cannot connect to coordinator: {e}")
        print(
            "  Make sure the coordinator is running on http://localhost:8000")
        return 1

    # Submit all workflow definitions
    print("\n" + "=" * 60)
    print("Submitting Workflows")
    print("=" * 60)
    submitted = submit_all_workflows(client)

    # List all workflows
    list_all_workflows(client)

    # Start a specific workflow
    if submitted:
        print("\n" + "=" * 60)
        print("Starting a Workflow")
        print("=" * 60)
        workflow_id = start_workflow_by_name(client, "simple-workflow")

        if workflow_id:
            # Monitor for a few seconds
            print("\nMonitoring for 10 seconds...")
            for i in range(5):
                time.sleep(2)
                workflow = client.get_workflow(workflow_id)
                print(f"  Status: {workflow.status}")

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
