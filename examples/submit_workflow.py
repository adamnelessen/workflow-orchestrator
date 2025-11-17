#!/usr/bin/env python3
"""Example script demonstrating how to submit and start workflows from YAML files."""

import argparse
import sys
import time
from pathlib import Path

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus


def main():
    """Submit and start a workflow from a YAML file."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Submit and start a workflow from a YAML file")
    parser.add_argument(
        "workflow_file",
        nargs="?",
        default="data-processing-pipeline.yaml",
        help=
        "Workflow definition filename (default: data-processing-pipeline.yaml)"
    )
    args = parser.parse_args()

    # Initialize client
    client = WorkflowClient(base_url="http://localhost:8000")

    # Path to the workflow definition
    yaml_path = Path(
        __file__).parent / "workflow_definitions" / args.workflow_file

    print(f"Submitting workflow from: {yaml_path}")

    # Submit and start the workflow
    try:
        workflow = client.submit_and_start_workflow(str(yaml_path))
        print(f"\n✓ Workflow submitted and started!")
        print(f"  ID: {workflow.id}")
        print(f"  Name: {workflow.name}")
        print(f"  Status: {workflow.status}")
        print(f"  Jobs: {len(workflow.jobs)}")

        # Monitor workflow execution
        print("\nMonitoring workflow execution...")
        workflow_id = workflow.id

        while True:
            time.sleep(2)
            workflow = client.get_workflow(workflow_id)
            print(f"  Status: {workflow.status}")

            if workflow.status in [
                    WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                    WorkflowStatus.CANCELLED
            ]:
                break

        print(f"\n✓ Workflow finished with status: {workflow.status}")

        # Print job details
        print("\nJob Details:")
        for job in workflow.jobs:
            print(f"  - {job.id}: {job.status}")

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
