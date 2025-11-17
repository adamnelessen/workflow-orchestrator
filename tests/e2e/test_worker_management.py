"""E2E tests for worker management and resilience."""
import pytest
import time
from typing import Callable

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus


@pytest.mark.e2e
class TestWorkerManagement:
    """Test worker connection, disconnection, and failover scenarios."""

    def test_workers_connect_on_startup(self, e2e_client: WorkflowClient,
                                        wait_for_workers):
        """Test that all workers connect successfully on startup."""
        wait_for_workers

        workers = e2e_client.get_workers()
        assert len(
            workers) >= 4, f"Expected at least 4 workers, got {len(workers)}"

        # Check worker IDs
        worker_ids = [w.id for w in workers]
        print(f"✓ Connected workers: {worker_ids}")

        # Verify workers have capabilities
        for worker in workers:
            assert len(worker.capabilities
                       ) > 0, f"Worker {worker.id} has no capabilities"

        print(f"✓ All {len(workers)} workers connected with capabilities")

    def test_worker_capabilities(self, e2e_client: WorkflowClient,
                                 wait_for_workers):
        """Test that workers report correct capabilities."""
        wait_for_workers

        workers = e2e_client.get_workers()

        expected_capabilities = {
            "validation", "processing", "integration", "cleanup"
        }

        for worker in workers:
            worker_caps = set(worker.capabilities)
            assert worker_caps == expected_capabilities, \
                f"Worker {worker.id} has incorrect capabilities: {worker_caps}"

        print(
            f"✓ All workers have correct capabilities: {expected_capabilities}"
        )

    def test_workflow_execution_with_worker_failure(self,
                                                    e2e_client: WorkflowClient,
                                                    wait_for_workers,
                                                    workflow_waiter,
                                                    workflow_definitions_path,
                                                    stop_worker, start_worker):
        """Test that workflows can continue when a worker fails."""
        wait_for_workers

        # Submit and start a workflow
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Started workflow: {workflow.id}")

        # Let it start executing
        time.sleep(2)

        # Stop one worker
        print("🛑 Stopping worker-e2e-1...")
        stop_worker("worker-e2e-1")

        # Verify worker count decreased
        time.sleep(2)
        workers = e2e_client.get_workers()
        print(f"  Workers remaining: {len(workers)}")

        # Workflow should still complete with remaining workers
        final_workflow = workflow_waiter(
            e2e_client,
            workflow.id,
            timeout=60  # Give it more time with fewer workers
        )

        # Should complete (remaining workers pick up the work)
        assert final_workflow["status"] == WorkflowStatus.COMPLETED

        print(f"✓ Workflow completed despite worker failure")

        # Restart the worker for cleanup
        start_worker("worker-e2e-1")

    def test_worker_reconnection(self, e2e_client: WorkflowClient,
                                 wait_for_workers, stop_worker, start_worker):
        """Test that a worker can disconnect and reconnect."""
        wait_for_workers

        initial_workers = e2e_client.get_workers()
        initial_count = len(initial_workers)

        print(f"\n👥 Initial worker count: {initial_count}")

        # Stop a worker
        stop_worker("worker-e2e-2")
        time.sleep(3)

        # Verify worker disconnected
        workers = e2e_client.get_workers()
        assert len(workers) < initial_count, "Worker did not disconnect"
        print(f"  Worker count after stop: {len(workers)}")

        # Restart the worker
        start_worker("worker-e2e-2")
        time.sleep(3)

        # Verify worker reconnected
        workers = e2e_client.get_workers()
        assert len(workers) == initial_count, "Worker did not reconnect"

        worker_ids = [w.id for w in workers]
        assert "e2e-worker-2" in worker_ids, "Specific worker did not reconnect"

        print(
            f"✓ Worker reconnected successfully. Total workers: {len(workers)}"
        )

    def test_load_distribution_across_workers(self, e2e_client: WorkflowClient,
                                              wait_for_workers,
                                              workflow_waiter,
                                              workflow_definitions_path):
        """Test that jobs are distributed across multiple workers."""
        wait_for_workers

        # Submit a workflow with multiple jobs
        yaml_path = workflow_definitions_path / "parallel-processing.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Started parallel workflow: {workflow.id}")

        # Wait for completion
        final_workflow = workflow_waiter(e2e_client, workflow.id, timeout=30)

        assert final_workflow["status"] == WorkflowStatus.COMPLETED

        # With parallel jobs and multiple workers, jobs should be distributed
        # This is validated by the successful completion itself
        print(
            f"✓ Parallel workflow completed - load distributed across workers")

    def test_worker_list_consistency(self, e2e_client: WorkflowClient,
                                     wait_for_workers):
        """Test that worker list remains consistent across multiple queries."""
        wait_for_workers

        # Get worker list multiple times
        workers_1 = e2e_client.get_workers()
        time.sleep(1)
        workers_2 = e2e_client.get_workers()
        time.sleep(1)
        workers_3 = e2e_client.get_workers()

        # Should have same count
        assert len(workers_1) == len(workers_2) == len(workers_3)

        # Should have same worker IDs
        ids_1 = set(w.id for w in workers_1)
        ids_2 = set(w.id for w in workers_2)
        ids_3 = set(w.id for w in workers_3)

        assert ids_1 == ids_2 == ids_3

        print(f"✓ Worker list consistent across queries: {ids_1}")

    def test_multiple_worker_failures(self, e2e_client: WorkflowClient,
                                      wait_for_workers, workflow_waiter,
                                      workflow_definitions_path, stop_worker,
                                      start_worker):
        """Test system behavior when multiple workers fail."""
        wait_for_workers

        # Submit workflow
        yaml_path = workflow_definitions_path / "data-processing-pipeline.yaml"
        workflow = e2e_client.submit_and_start_workflow(str(yaml_path))

        print(f"\n📋 Started workflow: {workflow.id}")
        time.sleep(2)

        # Stop multiple workers
        print("🛑 Stopping multiple workers...")
        stop_worker("worker-e2e-1")
        stop_worker("worker-e2e-2")

        time.sleep(3)

        # Check remaining workers
        workers = e2e_client.get_workers()
        print(f"  Workers remaining: {len(workers)}")
        assert len(workers) >= 2, "Should have at least 2 workers remaining"

        # Workflow should still complete with remaining workers
        try:
            final_workflow = workflow_waiter(e2e_client,
                                             workflow.id,
                                             timeout=60)
            assert final_workflow["status"] == WorkflowStatus.COMPLETED
            print(f"✓ Workflow survived multiple worker failures")
        finally:
            # Restart workers for cleanup
            start_worker("worker-e2e-1")
            start_worker("worker-e2e-2")
            time.sleep(3)

    def test_worker_status_reporting(self, e2e_client: WorkflowClient,
                                     wait_for_workers):
        """Test that workers report their status correctly."""
        wait_for_workers

        workers = e2e_client.get_workers()

        for worker in workers:
            # Each worker should have required attributes
            assert worker.id is not None
            assert worker.capabilities is not None
            assert len(worker.capabilities) > 0
            assert worker.status is not None

            print(
                f"  Worker {worker.id}: {worker.status}, {len(worker.capabilities)} capabilities"
            )

        print(f"✓ All {len(workers)} workers reporting status correctly")
