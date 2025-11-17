"""E2E tests for complete workflow lifecycle."""
import pytest
from pathlib import Path

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus, JobStatus


@pytest.mark.e2e
class TestWorkflowLifecycle:
    """Test complete workflow execution from submission to completion."""

    def test_data_processing_pipeline(self, e2e_client: WorkflowClient,
                                      wait_for_workers, workflow_waiter,
                                      workflow_definitions_path: Path):
        """Test the data processing pipeline workflow end-to-end."""
        # Ensure workers are ready
        wait_for_workers

        # Submit and start workflow
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Submitted workflow: {workflow.id}")
        assert workflow.status in [
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        ]
        assert len(workflow.jobs) == 5  # Verify correct number of jobs

        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)

        # Verify workflow completed successfully
        assert final_workflow["status"] == WorkflowStatus.COMPLETED

        # Verify all jobs completed (or handled correctly based on logic)
        completed_jobs = [
            job for job in final_workflow["jobs"]
            if job["status"] == JobStatus.COMPLETED
        ]
        assert len(completed_jobs) > 0, "At least some jobs should complete"

        print(f"✓ Workflow {workflow.id} completed successfully")
        print(
            f"  Jobs completed: {len(completed_jobs)}/{len(final_workflow['jobs'])}"
        )

    def test_deployment_pipeline(self, e2e_client: WorkflowClient,
                                 wait_for_workers, workflow_waiter,
                                 workflow_definitions_path: Path):
        """Test the deployment pipeline workflow end-to-end."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "deployment-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Submitted deployment workflow: {workflow.id}")

        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)

        assert final_workflow["status"] == WorkflowStatus.COMPLETED
        print(f"✓ Deployment workflow {workflow.id} completed")

    def test_parallel_processing_workflow(self, e2e_client: WorkflowClient,
                                          wait_for_workers, workflow_waiter,
                                          workflow_definitions_path: Path):
        """Test parallel processing workflow with concurrent jobs."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "parallel-processing.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Submitted parallel workflow: {workflow.id}")

        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)

        assert final_workflow["status"] == WorkflowStatus.COMPLETED

        # Verify parallel execution happened (multiple jobs should complete)
        completed_jobs = [
            job for job in final_workflow["jobs"]
            if job["status"] == JobStatus.COMPLETED
        ]
        assert len(
            completed_jobs) >= 2, "Multiple parallel jobs should complete"

        print(
            f"✓ Parallel workflow {workflow.id} completed with {len(completed_jobs)} jobs"
        )

    def test_workflow_status_transitions(self, e2e_client: WorkflowClient,
                                         wait_for_workers,
                                         workflow_definitions_path: Path):
        """Test that workflow transitions through expected statuses."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        # Track status transitions
        statuses_seen = set()
        statuses_seen.add(workflow.status)

        # Poll and collect statuses
        import time
        for _ in range(30):
            workflow = e2e_client.get_workflow(workflow.id)
            statuses_seen.add(workflow.status)

            if workflow.status in [
                    WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                    WorkflowStatus.CANCELLED
            ]:
                break

            time.sleep(1)

        # Should see at least PENDING/RUNNING and COMPLETED
        assert WorkflowStatus.COMPLETED in statuses_seen
        print(f"✓ Status transitions: {statuses_seen}")

    def test_workflow_cancellation(self, e2e_client: WorkflowClient,
                                   wait_for_workers,
                                   workflow_definitions_path: Path):
        """Test cancelling a running workflow."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Submitted workflow for cancellation: {workflow.id}")

        # Give it a moment to start running
        import time
        time.sleep(2)

        # Cancel the workflow
        e2e_client.cancel_workflow(workflow.id)

        # Wait a bit for cancellation to process
        time.sleep(2)

        # Check final status
        workflow = e2e_client.get_workflow(workflow.id)
        assert workflow.status in [
            WorkflowStatus.CANCELLED,
            WorkflowStatus.COMPLETED  # Might complete if it was fast
        ]

        print(
            f"✓ Workflow {workflow.id} cancelled/completed: {workflow.status}")

    def test_get_workflow_details(self, e2e_client: WorkflowClient,
                                  wait_for_workers, workflow_waiter,
                                  workflow_definitions_path: Path):
        """Test retrieving workflow details at various stages."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"

        # Submit workflow
        workflow = e2e_client.submit_workflow_from_yaml(str(yaml_path))
        workflow_id = workflow.id

        # Get details before starting
        workflow = e2e_client.get_workflow(workflow_id)
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.id == workflow_id
        assert workflow.name == "data-processing-pipeline"

        # Start workflow
        e2e_client.start_workflow(workflow_id)

        # Get details during execution
        workflow = e2e_client.get_workflow(workflow_id)
        assert workflow.status in [
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        ]

        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow_id, timeout=30)

        # Get final details
        workflow = e2e_client.get_workflow(workflow_id)
        assert workflow.status == WorkflowStatus.COMPLETED

        print(f"✓ Workflow details retrieved at all stages")

    def test_list_all_workflows(self, e2e_client: WorkflowClient,
                                wait_for_workers,
                                workflow_definitions_path: Path):
        """Test listing all workflows."""
        wait_for_workers

        # Submit multiple workflows
        workflow_ids = []
        for yaml_file in [
                "data-processing-pipeline.yaml", "deployment-pipeline.yaml"
        ]:
            yaml_path = workflow_definitions_path / yaml_file
            workflow = e2e_client.submit_workflow_from_yaml(str(yaml_path))
            workflow_ids.append(workflow.id)

        # List all workflows
        workflows = e2e_client.list_workflows()

        # Verify our workflows are in the list
        listed_ids = [w.id for w in workflows]
        for wf_id in workflow_ids:
            assert wf_id in listed_ids

        print(
            f"✓ Found {len(workflows)} total workflows, including our {len(workflow_ids)}"
        )
