"""Integration tests for PostgreSQL database operations"""
import pytest
from coordinator.db.postgres import PostgresDB
from shared.models import Workflow, Job, Worker
from shared.enums import JobStatus, JobType, WorkflowStatus, WorkerStatus
from datetime import datetime, UTC


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_save_and_retrieve_workflow(
    postgres_db: PostgresDB, sample_workflow: Workflow
) -> None:
    """Test saving and retrieving a workflow from PostgreSQL"""
    # Save workflow
    await postgres_db.save_workflow(sample_workflow)
    
    # Save jobs
    for job in sample_workflow.jobs:
        await postgres_db.save_job(job, sample_workflow.id)
    
    # Retrieve workflow
    retrieved = await postgres_db.get_workflow(sample_workflow.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_workflow.id
    assert retrieved.name == sample_workflow.name
    assert retrieved.status == sample_workflow.status
    
    # Retrieve jobs
    jobs = await postgres_db.list_jobs_by_workflow(sample_workflow.id)
    assert len(jobs) == 2
    assert jobs[0].id in ["test-job-1", "test-job-2"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_update_workflow(
    postgres_db: PostgresDB, sample_workflow: Workflow
) -> None:
    """Test updating a workflow in PostgreSQL"""
    # Save initial workflow
    await postgres_db.save_workflow(sample_workflow)
    
    # Update workflow status
    sample_workflow.status = WorkflowStatus.RUNNING
    sample_workflow.current_jobs = ["test-job-1"]
    await postgres_db.save_workflow(sample_workflow)
    
    # Retrieve and verify
    retrieved = await postgres_db.get_workflow(sample_workflow.id)
    assert retrieved.status == WorkflowStatus.RUNNING
    assert retrieved.current_jobs == ["test-job-1"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_list_workflows(postgres_db: PostgresDB) -> None:
    """Test listing all workflows"""
    # Create multiple workflows
    workflows = []
    for i in range(3):
        wf = Workflow(
            id=f"list-test-wf-{i}",
            name=f"Workflow {i}",
            status=WorkflowStatus.PENDING,
            jobs=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        workflows.append(wf)
        await postgres_db.save_workflow(wf)
    
    # List all workflows
    all_workflows = await postgres_db.list_workflows()
    
    # Should have at least our 3 workflows
    assert len(all_workflows) >= 3
    workflow_ids = [wf.id for wf in all_workflows]
    for wf in workflows:
        assert wf.id in workflow_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_delete_workflow(
    postgres_db: PostgresDB, sample_workflow: Workflow
) -> None:
    """Test deleting a workflow"""
    # Save workflow
    await postgres_db.save_workflow(sample_workflow)
    
    # Verify it exists
    retrieved = await postgres_db.get_workflow(sample_workflow.id)
    assert retrieved is not None
    
    # Delete it
    await postgres_db.delete_workflow(sample_workflow.id)
    
    # Verify it's gone
    retrieved = await postgres_db.get_workflow(sample_workflow.id)
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_save_and_retrieve_job(
    postgres_db: PostgresDB, sample_workflow: Workflow
) -> None:
    """Test saving and retrieving a job"""
    job = sample_workflow.jobs[0]
    
    # Save workflow first (foreign key requirement)
    await postgres_db.save_workflow(sample_workflow)
    
    # Save job
    await postgres_db.save_job(job, sample_workflow.id)
    
    # Retrieve job
    retrieved = await postgres_db.get_job(job.id)
    
    assert retrieved is not None
    assert retrieved.id == job.id
    assert retrieved.type == job.type
    assert retrieved.status == job.status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_update_job_status(
    postgres_db: PostgresDB, sample_workflow: Workflow
) -> None:
    """Test updating job status"""
    job = sample_workflow.jobs[0]
    
    # Save workflow and job
    await postgres_db.save_workflow(sample_workflow)
    await postgres_db.save_job(job, sample_workflow.id)
    
    # Update job
    job.status = JobStatus.RUNNING
    job.worker_id = "worker-1"
    await postgres_db.save_job(job, sample_workflow.id)
    
    # Retrieve and verify
    retrieved = await postgres_db.get_job(job.id)
    assert retrieved.status == JobStatus.RUNNING
    assert retrieved.worker_id == "worker-1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_save_and_retrieve_worker(
    postgres_db: PostgresDB, sample_worker: Worker
) -> None:
    """Test saving and retrieving a worker"""
    # Save worker
    await postgres_db.save_worker(sample_worker)
    
    # Retrieve worker
    retrieved = await postgres_db.get_worker(sample_worker.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_worker.id
    assert retrieved.status == sample_worker.status
    assert len(retrieved.capabilities) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_list_workers(postgres_db: PostgresDB) -> None:
    """Test listing all workers"""
    # Create multiple workers
    workers = []
    for i in range(3):
        worker = Worker(
            id=f"list-test-worker-{i}",
            status=WorkerStatus.IDLE,
            capabilities=[JobType.VALIDATION],
            last_heartbeat=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        workers.append(worker)
        await postgres_db.save_worker(worker)
    
    # List all workers
    all_workers = await postgres_db.list_workers()
    
    # Should have at least our 3 workers
    assert len(all_workers) >= 3
    worker_ids = [w.id for w in all_workers]
    for worker in workers:
        assert worker.id in worker_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_delete_worker(
    postgres_db: PostgresDB, sample_worker: Worker
) -> None:
    """Test deleting a worker"""
    # Save worker
    await postgres_db.save_worker(sample_worker)
    
    # Verify it exists
    retrieved = await postgres_db.get_worker(sample_worker.id)
    assert retrieved is not None
    
    # Delete it
    await postgres_db.delete_worker(sample_worker.id)
    
    # Verify it's gone
    retrieved = await postgres_db.get_worker(sample_worker.id)
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_job_assignments(postgres_db: PostgresDB) -> None:
    """Test job assignment operations"""
    # Save assignment
    await postgres_db.save_assignment("job-1", "worker-1")
    
    # Retrieve assignment
    worker_id = await postgres_db.get_assignment("job-1")
    assert worker_id == "worker-1"
    
    # List all assignments
    all_assignments = await postgres_db.list_all_assignments()
    assert len(all_assignments) >= 1
    
    job_ids = [a.job_id for a in all_assignments]
    assert "job-1" in job_ids
    
    # Delete assignment
    await postgres_db.delete_assignment("job-1")
    
    # Verify it's gone
    worker_id = await postgres_db.get_assignment("job-1")
    assert worker_id is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_multiple_assignments(postgres_db: PostgresDB) -> None:
    """Test multiple job assignments"""
    # Create multiple assignments
    assignments = [
        ("job-a", "worker-1"),
        ("job-b", "worker-1"),
        ("job-c", "worker-2"),
    ]
    
    for job_id, worker_id in assignments:
        await postgres_db.save_assignment(job_id, worker_id)
    
    # List all and verify
    all_assignments = await postgres_db.list_all_assignments()
    
    assignment_dict = {a.job_id: a.worker_id for a in all_assignments}
    assert "job-a" in assignment_dict
    assert assignment_dict["job-a"] == "worker-1"
    assert assignment_dict["job-b"] == "worker-1"
    assert assignment_dict["job-c"] == "worker-2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
