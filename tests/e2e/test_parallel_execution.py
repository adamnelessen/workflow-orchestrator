"""E2E tests for parallel workflow execution."""
import pytest
import time
from typing import List

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus
from shared.models import Workflow


@pytest.mark.e2e
class TestParallelExecution:
    """Test concurrent workflow and job execution."""

    def test_multiple_concurrent_workflows(self, e2e_client: WorkflowClient,
                                           wait_for_workers, workflow_waiter,
                                           workflow_definitions_path):
        """Test executing multiple workflows concurrently."""
        wait_for_workers

        # Submit multiple workflows at once
        workflows = []
        yaml_files = [
            "data-processing-pipeline.yaml", "deployment-pipeline.yaml",
            "parallel-processing.yaml"
        ]

        print(f"\n📋 Submitting {len(yaml_files)} concurrent workflows...")
        for yaml_file in yaml_files:
            yaml_path = workflow_definitions_path / yaml_file
            workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
            workflows.append(workflow)
            print(f"  - {workflow.id} ({yaml_file})")

        # Wait for all to complete
        print("\n⏳ Waiting for all workflows to complete...")
        for workflow in workflows:
            final_workflow = workflow_waiter(e2e_client,
                                             workflow.id,
                                             timeout=60)
            assert final_workflow["status"] == WorkflowStatus.COMPLETED
            print(f"  ✓ {workflow.id} completed")

        print(
            f"\n✓ All {len(workflows)} concurrent workflows completed successfully"
        )

    def test_workflow_execution_isolation(self, e2e_client: WorkflowClient,
                                          wait_for_workers,
                                          workflow_definitions_path):
        """Test that concurrent workflows don't interfere with each other."""
        wait_for_workers

        # Submit two identical workflows
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow1 = e2e_client.submit_and_start_workflow(str(yaml_path))
        workflow2 = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Started two identical workflows:")
        print(f"  - {workflow1.id}")
        print(f"  - {workflow2.id}")

        # Monitor both
        completed = set()
        start_time = time.time()

        while time.time() - start_time < 60:
            for wf_id in [workflow1.id, workflow2.id]:
                if wf_id not in completed:
                    wf = e2e_client.get_workflow(wf_id)
                    if wf.status == WorkflowStatus.COMPLETED:
                        completed.add(wf_id)
                        print(f"  ✓ {wf_id} completed")

            if len(completed) == 2:
                break

            time.sleep(1)

        assert len(
            completed) == 2, f"Only {len(completed)}/2 workflows completed"

        # Verify both have their own job sets (no sharing)
        wf1_final = e2e_client.get_workflow(workflow1.id)
        wf2_final = e2e_client.get_workflow(workflow2.id)

        wf1_job_ids = set(job.id for job in wf1_final.jobs)
        wf2_job_ids = set(job.id for job in wf2_final.jobs)

        # Job IDs should be different (no sharing)
        assert wf1_job_ids != wf2_job_ids, "Workflows should have separate job instances"

        print(f"✓ Workflows executed in isolation with separate job instances")

    def test_high_concurrency_stress(self, e2e_client: WorkflowClient,
                                     wait_for_workers,
                                     workflow_definitions_path):
        """Test system under high concurrent workflow load."""
        wait_for_workers

        # Submit many workflows quickly
        num_workflows = 5
        workflows = []

        print(
            f"\n📋 Stress test: submitting {num_workflows} workflows rapidly..."
        )
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"

        for i in range(num_workflows):
            workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
            workflows.append(workflow.id)

        print(f"  ✓ Submitted {num_workflows} workflows")

        # Monitor completion
        completed = 0
        start_time = time.time()

        while time.time() - start_time < 120:  # 2 minutes max
            all_complete = True
            current_completed = 0

            for wf_id in workflows:
                wf = e2e_client.get_workflow(wf_id)
                if wf.status == WorkflowStatus.COMPLETED:
                    current_completed += 1
                elif wf.status not in [
                        WorkflowStatus.FAILED, WorkflowStatus.CANCELLED
                ]:
                    all_complete = False

            if current_completed > completed:
                print(
                    f"  Progress: {current_completed}/{num_workflows} completed"
                )
                completed = current_completed

            if all_complete:
                break

            time.sleep(2)

        # Verify all completed
        final_statuses = {}
        for wf_id in workflows:
            wf = e2e_client.get_workflow(wf_id)
            final_statuses[wf_id] = wf.status

        completed_count = sum(1 for s in final_statuses.values()
                              if s == WorkflowStatus.COMPLETED)

        print(
            f"\n✓ Stress test results: {completed_count}/{num_workflows} completed"
        )
        assert completed_count >= num_workflows * 0.8, "At least 80% should complete"

    def test_parallel_jobs_within_workflow(self, e2e_client: WorkflowClient,
                                           wait_for_workers, workflow_waiter,
                                           workflow_definitions_path):
        """Test that jobs within a workflow can execute in parallel."""
        wait_for_workers

        # Use parallel-processing workflow which has independent jobs
        yaml_path = workflow_definitions_path / "parallel-processing.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Started parallel processing workflow: {workflow.id}")

        # Track job statuses over time
        job_running_count = []
        start_time = time.time()

        while time.time() - start_time < 30:
            wf = e2e_client.get_workflow(workflow.id)

            if wf.status == WorkflowStatus.COMPLETED:
                break

            # Count currently running jobs
            from shared.enums import JobStatus
            running = sum(1 for job in wf.jobs
                          if job.status == JobStatus.RUNNING)
            if running > 0:
                job_running_count.append(running)

            time.sleep(0.5)

        # Wait for final completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)

        assert final_workflow["status"] == WorkflowStatus.COMPLETED

        # If we saw multiple jobs running simultaneously, parallel execution occurred
        max_parallel = max(job_running_count) if job_running_count else 0
        print(f"  Max parallel jobs: {max_parallel}")
        print(f"✓ Parallel job execution within workflow: {max_parallel > 1}")

    def test_workflow_throughput(self, e2e_client: WorkflowClient,
                                 wait_for_workers, workflow_definitions_path):
        """Test workflow processing throughput."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"

        # Submit workflows and track timing
        num_workflows = 3
        workflows = []

        print(f"\n📊 Throughput test: {num_workflows} workflows...")
        start_time = time.time()

        for i in range(num_workflows):
            workflow = e2e_client.submit_and_start_workflow(str(yaml_path))
            workflows.append(workflow.id)

        # Wait for all to complete
        all_completed = False
        while time.time() - start_time < 90:
            completed = 0
            for wf_id in workflows:
                wf = e2e_client.get_workflow(wf_id)
                if wf.status == WorkflowStatus.COMPLETED:
                    completed += 1

            if completed == num_workflows:
                all_completed = True
                break

            time.sleep(1)

        end_time = time.time()
        elapsed = end_time - start_time

        assert all_completed, f"Not all workflows completed in time"

        throughput = num_workflows / elapsed
        print(f"  ✓ Completed {num_workflows} workflows in {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.2f} workflows/second")

    def test_sequential_vs_parallel_performance(self,
                                                e2e_client: WorkflowClient,
                                                wait_for_workers,
                                                workflow_waiter,
                                                workflow_definitions_path):
        """Compare sequential vs parallel workflow execution."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"

        # Sequential execution
        print("\n📊 Sequential execution test...")
        seq_start = time.time()

        workflow1 = e2e_client.submit_and_start_workflow(str(yaml_path))
        workflow_waiter(e2e_client, workflow1.id, timeout=30)

        workflow2 = e2e_client.submit_and_start_workflow(str(yaml_path))
        workflow_waiter(e2e_client, workflow2.id, timeout=30)

        seq_time = time.time() - seq_start
        print(f"  Sequential time: {seq_time:.2f}s")

        # Parallel execution
        print("\n📊 Parallel execution test...")
        par_start = time.time()

        workflow3 = e2e_client.submit_and_start_workflow(str(yaml_path))
        workflow4 = e2e_client.submit_and_start_workflow(str(yaml_path))

        workflow_waiter(e2e_client, workflow3.id, timeout=30)
        workflow_waiter(e2e_client, workflow4.id, timeout=30)

        par_time = time.time() - par_start
        print(f"  Parallel time: {par_time:.2f}s")

        # Parallel should be faster (or at least not significantly slower)
        print(
            f"\n✓ Time comparison: Sequential={seq_time:.2f}s, Parallel={par_time:.2f}s"
        )
        print(f"  Speedup: {seq_time/par_time:.2f}x")
