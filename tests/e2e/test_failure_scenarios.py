"""E2E tests for failure scenarios and edge cases."""
import pytest
import time
from pathlib import Path

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus, JobStatus


@pytest.mark.e2e
class TestFailureScenarios:
    """Test system behavior under failure conditions and edge cases."""

    def test_invalid_workflow_yaml(self, e2e_client: WorkflowClient,
                                   wait_for_workers, tmp_path: Path):
        """Test submitting an invalid workflow YAML."""
        wait_for_workers

        # Create invalid YAML file
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("this is not valid yaml: ][")

        # Should raise an error
        with pytest.raises(Exception):
            e2e_client.submit_workflow_from_yaml(str(invalid_yaml))

        print("✓ Invalid YAML rejected as expected")

    def test_nonexistent_workflow_file(self, e2e_client: WorkflowClient,
                                       wait_for_workers):
        """Test submitting a workflow from a nonexistent file."""
        wait_for_workers

        with pytest.raises(FileNotFoundError):
            e2e_client.submit_workflow_from_yaml(
                "/nonexistent/path/workflow.yaml")

        print("✓ Nonexistent file error raised as expected")

    def test_get_nonexistent_workflow(self, e2e_client: WorkflowClient,
                                      wait_for_workers):
        """Test retrieving a workflow that doesn't exist."""
        wait_for_workers

        with pytest.raises(Exception) as exc_info:
            e2e_client.get_workflow("nonexistent-workflow-id")

        # Should get 404 or similar error
        assert "404" in str(exc_info.value) or "not found" in str(
            exc_info.value).lower()

        print("✓ Nonexistent workflow error raised as expected")

    def test_cancel_already_completed_workflow(self,
                                               e2e_client: WorkflowClient,
                                               wait_for_workers,
                                               workflow_waiter,
                                               workflow_definitions_path):
        """Test cancelling a workflow that's already completed."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        # Wait for completion
        workflow_waiter(e2e_client, workflow.id, timeout=30)

        # Try to cancel completed workflow
        try:
            e2e_client.cancel_workflow(workflow.id)
            # Should either succeed silently or raise an error
            print("✓ Cancel on completed workflow handled")
        except Exception as e:
            # Error is acceptable
            print(
                f"✓ Cancel on completed workflow raised error (acceptable): {type(e).__name__}"
            )

    def test_start_already_running_workflow(self, e2e_client: WorkflowClient,
                                            wait_for_workers,
                                            workflow_definitions_path):
        """Test starting a workflow that's already running."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        # Try to start it again immediately
        try:
            e2e_client.start_workflow(workflow.id)
            print("✓ Double start handled gracefully")
        except Exception as e:
            # Error is acceptable
            print(
                f"✓ Double start raised error (acceptable): {type(e).__name__}"
            )

    def test_workflow_with_no_workers_available(self,
                                                e2e_client: WorkflowClient,
                                                wait_for_workers,
                                                workflow_definitions_path,
                                                stop_worker, start_worker):
        """Test workflow behavior when no workers are available."""
        wait_for_workers

        # Stop all workers
        print("\n🛑 Stopping all workers...")
        for i in range(1, 5):
            stop_worker(f"worker-e2e-{i}")

        time.sleep(3)

        # Verify no workers
        workers = e2e_client.get_workers()
        print(f"  Active workers: {len(workers)}")

        # Submit a workflow
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"📋 Submitted workflow with no workers: {workflow.id}")

        # Workflow should remain in pending/running state
        time.sleep(5)
        workflow = e2e_client.get_workflow(workflow.id)

        # Should not be completed (no workers to process it)
        assert workflow.status in [
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        ]

        print(f"✓ Workflow correctly waiting for workers: {workflow.status}")

        # Restart workers for subsequent tests
        print("\n🟢 Restarting all workers...")
        for i in range(1, 5):
            start_worker(f"worker-e2e-{i}")

        time.sleep(3)  # Give them time to reconnect

    def test_rapid_workflow_submission(self, e2e_client: WorkflowClient,
                                       wait_for_workers,
                                       workflow_definitions_path):
        """Test submitting many workflows very quickly."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"

        # Submit many workflows as fast as possible
        num_workflows = 10
        workflow_ids = []

        print(f"\n⚡ Rapidly submitting {num_workflows} workflows...")
        start = time.time()

        for i in range(num_workflows):
            try:
                workflow = e2e_client.submit_workflow_from_yaml(str(yaml_path))
                workflow_ids.append(workflow.id)
            except Exception as e:
                print(f"  Error on submission {i}: {e}")

        elapsed = time.time() - start
        print(
            f"  Submitted {len(workflow_ids)}/{num_workflows} in {elapsed:.2f}s"
        )

        # At least most should succeed
        assert len(workflow_ids) >= num_workflows * 0.9

        print("✓ Rapid submission handled successfully")

    def test_workflow_timeout_scenario(self, e2e_client: WorkflowClient,
                                       wait_for_workers, workflow_waiter,
                                       workflow_definitions_path):
        """Test workflow with intentionally short timeout."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Testing timeout with workflow: {workflow.id}")

        # Use a very short timeout on purpose
        try:
            workflow_waiter(e2e_client, workflow.id, timeout=1)
            print("  Workflow completed within timeout")
        except TimeoutError:
            print("✓ Timeout raised as expected")
            # This is expected - workflow might not finish in 1 second

    def test_empty_workflow_list(self, e2e_client: WorkflowClient,
                                 wait_for_workers):
        """Test listing workflows when state is clean."""
        wait_for_workers

        # Get current workflows (might have some from previous tests in session)
        workflows = e2e_client.list_workflows()

        # Should return a list (empty or not)
        assert isinstance(workflows, list)

        print(f"✓ List workflows returned {len(workflows)} workflows")

    def test_workflow_with_missing_dependencies(self,
                                                e2e_client: WorkflowClient,
                                                wait_for_workers,
                                                tmp_path: Path):
        """Test workflow with job dependencies that don't exist."""
        wait_for_workers

        # Create workflow with invalid dependency
        invalid_workflow = tmp_path / "invalid_deps.yaml"
        invalid_workflow.write_text("""
workflow:
  name: "invalid-dependencies"
  jobs:
    - id: "job-1"
      type: "validation"
      on_success: "nonexistent-job"
""")

        # Try to submit - should either reject or handle gracefully
        try:
            workflow = e2e_client.submit_workflow_from_yaml(
                str(invalid_workflow))
            print(f"  Workflow submitted: {workflow.id}")

            # Try to start it
            e2e_client.start_workflow(workflow.id)

            # Monitor for a bit
            time.sleep(5)
            workflow = e2e_client.get_workflow(workflow.id)

            print(f"✓ Invalid dependencies handled, status: {workflow.status}")

        except Exception as e:
            # Rejection is also acceptable
            print(f"✓ Invalid dependencies rejected: {type(e).__name__}")

    def test_concurrent_operations_on_same_workflow(self,
                                                    e2e_client: WorkflowClient,
                                                    wait_for_workers,
                                                    workflow_definitions_path):
        """Test concurrent reads/operations on the same workflow."""
        wait_for_workers

        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Testing concurrent operations on: {workflow.id}")

        # Rapidly query the same workflow multiple times
        import concurrent.futures

        def get_workflow_status():
            try:
                wf = e2e_client.get_workflow(workflow.id)
                return wf.status
            except Exception as e:
                return f"Error: {type(e).__name__}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_workflow_status) for _ in range(10)]
            results = [
                f.result() for f in concurrent.futures.as_completed(futures)
            ]

        # Should get valid statuses (not errors)
        valid_results = [r for r in results if not str(r).startswith("Error")]

        assert len(valid_results) >= 8, "Most concurrent reads should succeed"
        print(
            f"✓ Concurrent operations handled: {len(valid_results)}/10 succeeded"
        )

    def test_health_check_during_load(self, e2e_client: WorkflowClient,
                                      wait_for_workers,
                                      workflow_definitions_path):
        """Test that health endpoint remains responsive under load."""
        wait_for_workers

        # Start several workflows
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        for i in range(3):
            e2e_client.submit_and_start_workflow(str(yaml_path))

        # Check health repeatedly
        import requests
        health_url = e2e_client.base_url + "/health"

        successes = 0
        for i in range(10):
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    successes += 1
            except Exception:
                pass
            time.sleep(0.5)

        # Health should remain responsive
        assert successes >= 8, "Health endpoint should remain responsive under load"
        print(f"✓ Health check responsive: {successes}/10 succeeded")
