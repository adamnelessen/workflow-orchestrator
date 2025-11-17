"""Quick validation test for database integration"""
import pytest
from coordinator.core.state_manager import StateManager
from shared.models import Workflow, Job
from shared.enums import JobStatus, JobType, WorkflowStatus
from datetime import datetime, UTC


def test_state_manager_in_memory_mode():
    """Test that StateManager works without databases (backward compatibility)"""
    state = StateManager()

    # Create a simple workflow
    job = Job(
        id="test-job-1",
        type=JobType.VALIDATION,
        parameters={"test": "data"},
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    workflow = Workflow(
        id="test-workflow-1",
        name="Test Workflow",
        status=WorkflowStatus.PENDING,
        jobs=[job],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Test sync methods (original API)
    state.add_workflow(workflow)
    retrieved = state.get_workflow("test-workflow-1")

    assert retrieved is not None
    assert retrieved.id == "test-workflow-1"
    assert retrieved.name == "Test Workflow"
    assert len(retrieved.jobs) == 1

    # Test job retrieval
    retrieved_job = state.get_job("test-job-1")
    assert retrieved_job is not None
    assert retrieved_job.id == "test-job-1"


def test_state_manager_job_assignments():
    """Test job assignment tracking"""
    state = StateManager()

    # Test job assignments
    state.assign_job("job-1", "worker-1")
    state.assign_job("job-2", "worker-1")
    state.assign_job("job-3", "worker-2")

    # Test retrieval
    assert state.get_job_worker("job-1") == "worker-1"
    assert state.count_worker_jobs("worker-1") == 2
    assert state.count_worker_jobs("worker-2") == 1

    # Test worker job list
    worker_1_jobs = state.get_worker_jobs("worker-1")
    assert len(worker_1_jobs) == 2
    assert "job-1" in worker_1_jobs
    assert "job-2" in worker_1_jobs


@pytest.mark.asyncio
async def test_state_manager_has_async_methods():
    """Test that async methods are available"""
    state = StateManager()

    job = Job(
        id="async-job-1",
        type=JobType.PROCESSING,
        parameters={},
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    workflow = Workflow(
        id="async-workflow-1",
        name="Async Test",
        status=WorkflowStatus.PENDING,
        jobs=[job],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Test async methods exist and work (even without databases)
    await state.add_workflow_async(workflow)
    retrieved = await state.get_workflow_async("async-workflow-1")

    assert retrieved is not None
    assert retrieved.id == "async-workflow-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
