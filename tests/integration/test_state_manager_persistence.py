"""Integration tests for StateManager with full database persistence"""
import pytest
import os
from coordinator.core.state_manager import StateManager, init_state_manager
from shared.models import Workflow, Job, Worker
from shared.enums import JobStatus, JobType, WorkflowStatus, WorkerStatus
from datetime import datetime, UTC


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_persists_to_postgres(
    full_state_manager: StateManager, sample_workflow: Workflow
) -> None:
    """Test that adding a workflow persists it to PostgreSQL"""
    # Add workflow through StateManager
    await full_state_manager.add_workflow(sample_workflow)
    
    # Verify in memory
    assert sample_workflow.id in full_state_manager.workflows
    
    # Verify in PostgreSQL directly
    pg_workflow = await full_state_manager.postgres.get_workflow(sample_workflow.id)
    assert pg_workflow is not None
    assert pg_workflow.id == sample_workflow.id
    assert pg_workflow.name == sample_workflow.name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_cached_in_redis(
    full_state_manager: StateManager, sample_workflow: Workflow
) -> None:
    """Test that adding a workflow caches it in Redis"""
    # Add workflow through StateManager
    await full_state_manager.add_workflow(sample_workflow)
    
    # Verify in Redis cache directly
    cached = await full_state_manager.redis.get_cached_workflow(sample_workflow.id)
    assert cached is not None
    assert cached["id"] == sample_workflow.id
    assert cached["name"] == sample_workflow.name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_three_tier_read_path(
    full_state_manager: StateManager, sample_workflow: Workflow
) -> None:
    """Test the three-tier read path: memory -> Redis -> PostgreSQL"""
    # Add workflow
    await full_state_manager.add_workflow(sample_workflow)
    
    # Clear in-memory cache to test Redis fetch
    full_state_manager.workflows.clear()
    full_state_manager.jobs.clear()
    
    # Get workflow (should come from Redis)
    retrieved = await full_state_manager.get_workflow(sample_workflow.id)
    assert retrieved is not None
    assert retrieved.id == sample_workflow.id
    
    # Verify it was restored to memory
    assert sample_workflow.id in full_state_manager.workflows
    
    # Clear both memory and Redis to test PostgreSQL fetch
    full_state_manager.workflows.clear()
    full_state_manager.jobs.clear()
    await full_state_manager.redis.invalidate_workflow(sample_workflow.id)
    for job in sample_workflow.jobs:
        await full_state_manager.redis.invalidate_job(job.id)
    
    # Get workflow (should come from PostgreSQL)
    retrieved = await full_state_manager.get_workflow(sample_workflow.id)
    assert retrieved is not None
    assert retrieved.id == sample_workflow.id
    assert len(retrieved.jobs) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rebuild_from_db_after_restart(
    sample_workflow: Workflow, sample_worker: Worker
) -> None:
    """Test that StateManager rebuilds in-memory cache from PostgreSQL on init"""
    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Create first StateManager instance
    state1 = await init_state_manager(database_url, redis_url)
    
    # Add workflow and worker
    await state1.add_workflow(sample_workflow)
    await state1.add_worker(sample_worker)
    await state1.assign_job(sample_workflow.jobs[0].id, sample_worker.id)
    
    # Verify they're in memory
    assert sample_workflow.id in state1.workflows
    assert sample_worker.id in state1.workers
    assert sample_workflow.jobs[0].id in state1.job_assignments
    
    # Close first instance
    if state1.postgres:
        await state1.postgres.close()
    if state1.redis:
        await state1.redis.close()
    
    # Create second StateManager instance (simulates restart)
    state2 = await init_state_manager(database_url, redis_url)
    
    # Verify data was rebuilt from PostgreSQL
    assert sample_workflow.id in state2.workflows
    assert sample_worker.id in state2.workers
    assert sample_workflow.jobs[0].id in state2.job_assignments
    
    # Verify workflow details are correct
    rebuilt_workflow = state2.workflows[sample_workflow.id]
    assert rebuilt_workflow.name == sample_workflow.name
    assert len(rebuilt_workflow.jobs) == 2
    
    # Verify worker details are correct
    rebuilt_worker = state2.workers[sample_worker.id]
    assert rebuilt_worker.status == sample_worker.status
    assert len(rebuilt_worker.capabilities) == 2
    
    # Verify assignment is correct
    assert state2.job_assignments[sample_workflow.jobs[0].id] == sample_worker.id
    
    # Cleanup
    await state2.postgres.close()
    await state2.redis.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_persistence(
    full_state_manager: StateManager, sample_worker: Worker
) -> None:
    """Test that workers are persisted to PostgreSQL"""
    # Add worker
    await full_state_manager.add_worker(sample_worker)
    
    # Verify in PostgreSQL
    pg_worker = await full_state_manager.postgres.get_worker(sample_worker.id)
    assert pg_worker is not None
    assert pg_worker.id == sample_worker.id
    assert pg_worker.status == sample_worker.status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_assignment_persistence(
    full_state_manager: StateManager, sample_workflow: Workflow, sample_worker: Worker
) -> None:
    """Test that job assignments are persisted"""
    # Add workflow and worker
    await full_state_manager.add_workflow(sample_workflow)
    await full_state_manager.add_worker(sample_worker)
    
    # Assign job
    job_id = sample_workflow.jobs[0].id
    await full_state_manager.assign_job(job_id, sample_worker.id)
    
    # Verify in memory
    assert full_state_manager.job_assignments[job_id] == sample_worker.id
    
    # Verify in PostgreSQL
    pg_assignment = await full_state_manager.postgres.get_assignment(job_id)
    assert pg_assignment == sample_worker.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_removal_cascades(
    full_state_manager: StateManager, sample_workflow: Workflow
) -> None:
    """Test that removing a workflow clears it from all storage layers"""
    # Add workflow
    await full_state_manager.add_workflow(sample_workflow)
    
    # Verify it's everywhere
    assert sample_workflow.id in full_state_manager.workflows
    pg_wf = await full_state_manager.postgres.get_workflow(sample_workflow.id)
    assert pg_wf is not None
    redis_wf = await full_state_manager.redis.get_cached_workflow(sample_workflow.id)
    assert redis_wf is not None
    
    # Remove workflow
    await full_state_manager.remove_workflow(sample_workflow.id)
    
    # Verify it's gone from all layers
    assert sample_workflow.id not in full_state_manager.workflows
    pg_wf = await full_state_manager.postgres.get_workflow(sample_workflow.id)
    assert pg_wf is None
    redis_wf = await full_state_manager.redis.get_cached_workflow(sample_workflow.id)
    assert redis_wf is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_workflows_after_restart() -> None:
    """Test that list_workflows returns all workflows after restart"""
    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Create first instance and add multiple workflows
    state1 = await init_state_manager(database_url, redis_url)
    
    workflows = []
    for i in range(3):
        wf = Workflow(
            id=f"list-restart-wf-{i}",
            name=f"Restart Test Workflow {i}",
            status=WorkflowStatus.PENDING,
            jobs=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        workflows.append(wf)
        await state1.add_workflow(wf)
    
    # Close first instance
    if state1.postgres:
        await state1.postgres.close()
    if state1.redis:
        await state1.redis.close()
    
    # Create second instance
    state2 = await init_state_manager(database_url, redis_url)
    
    # List workflows should return all of them
    listed_workflows = state2.list_workflows()
    workflow_ids = [wf.id for wf in listed_workflows]
    
    for wf in workflows:
        assert wf.id in workflow_ids
    
    # Cleanup
    await state2.postgres.close()
    await state2.redis.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_update_propagates(
    full_state_manager: StateManager, sample_workflow: Workflow
) -> None:
    """Test that job updates propagate to PostgreSQL"""
    # Add workflow
    await full_state_manager.add_workflow(sample_workflow)
    
    # Update job status
    job = sample_workflow.jobs[0]
    job.status = JobStatus.RUNNING
    job.worker_id = "test-worker"
    
    # Save update
    await full_state_manager.add_job(job)
    
    # Verify in PostgreSQL
    pg_job = await full_state_manager.postgres.get_job(job.id)
    assert pg_job.status == JobStatus.RUNNING
    assert pg_job.worker_id == "test-worker"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
