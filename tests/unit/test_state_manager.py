"""Unit tests for StateManager"""
import pytest
from datetime import datetime, UTC
from typing import Callable

from coordinator.core.state_manager import StateManager
from shared.enums import WorkflowStatus, WorkerStatus
from shared.models import Workflow, Worker


@pytest.mark.unit
class TestStateManager:
    """Test StateManager operations"""

    async def test_add_workflow(self, state_manager: StateManager,
                          workflow_factory: Callable[..., Workflow]) -> None:
        """Test adding a workflow"""
        workflow = workflow_factory(workflow_id="wf-1")

        await state_manager.add_workflow(workflow)

        assert await state_manager.get_workflow("wf-1") == workflow
        assert len(state_manager.list_workflows()) == 1

    async def test_get_nonexistent_workflow(self,
                                      state_manager: StateManager) -> None:
        """Test getting a workflow that doesn't exist"""
        result = await state_manager.get_workflow("nonexistent")

        assert result is None

    async def test_remove_workflow(
            self, state_manager: StateManager,
            workflow_factory: Callable[..., Workflow]) -> None:
        """Test removing a workflow"""
        workflow = workflow_factory(workflow_id="wf-1")
        await state_manager.add_workflow(workflow)

        await state_manager.remove_workflow("wf-1")

        assert await state_manager.get_workflow("wf-1") is None
        assert len(state_manager.list_workflows()) == 0

    async def test_add_worker(self, state_manager: StateManager,
                        worker_factory: Callable[..., Worker]) -> None:
        """Test adding a worker"""
        worker = worker_factory(worker_id="worker-1")

        await state_manager.add_worker(worker)

        assert await state_manager.get_worker("worker-1") == worker
        assert len(state_manager.list_workers()) == 1

    async def test_assign_job(self, state_manager: StateManager) -> None:
        """Test job assignment"""
        await state_manager.assign_job("job-1", "worker-1")

        assert await state_manager.get_job_worker("job-1") == "worker-1"

    async def test_unassign_job(self, state_manager: StateManager) -> None:
        """Test job unassignment"""
        await state_manager.assign_job("job-1", "worker-1")
        await state_manager.unassign_job("job-1")

        assert await state_manager.get_job_worker("job-1") is None

    def test_list_workflows(self, populated_state: StateManager) -> None:
        """Test listing all workflows"""
        workflows = populated_state.list_workflows()

        assert len(workflows) == 2
        assert all(hasattr(w, 'id') for w in workflows)

    def test_list_workers(self, populated_state: StateManager) -> None:
        """Test listing all workers"""
        workers = populated_state.list_workers()

        assert len(workers) == 2
        assert all(hasattr(w, 'id') for w in workers)


@pytest.mark.unit
class TestStateManagerConcurrency:
    """Test StateManager thread safety (if applicable)"""

    async def test_multiple_workflow_adds(
            self, state_manager: StateManager,
            workflow_factory: Callable[..., Workflow]) -> None:
        """Test adding multiple workflows"""
        workflows = [workflow_factory(workflow_id=f"wf-{i}") for i in range(5)]

        for wf in workflows:
            await state_manager.add_workflow(wf)

        assert len(state_manager.list_workflows()) == 5

    async def test_duplicate_workflow_id(
            self, state_manager: StateManager,
            workflow_factory: Callable[..., Workflow]) -> None:
        """Test handling duplicate workflow IDs"""
        wf1 = workflow_factory(workflow_id="wf-1", name="First")
        wf2 = workflow_factory(workflow_id="wf-1", name="Second")

        await state_manager.add_workflow(wf1)
        await state_manager.add_workflow(wf2)  # Should overwrite

        result = await state_manager.get_workflow("wf-1")
        assert result.name == "Second"
