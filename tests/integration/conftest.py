"""Integration test fixtures"""
import pytest
from shared.models import Workflow, Job, Worker
from shared.enums import JobStatus, JobType, WorkflowStatus, WorkerStatus
from datetime import datetime, UTC


@pytest.fixture
def sample_workflow() -> Workflow:
    """Create a sample workflow for testing"""
    job1 = Job(
        id="test-job-1",
        type=JobType.VALIDATION,
        parameters={"test": "data"},
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    job2 = Job(
        id="test-job-2",
        type=JobType.PROCESSING,
        parameters={"process": "data"},
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    return Workflow(
        id="test-workflow-1",
        name="Test Workflow",
        status=WorkflowStatus.PENDING,
        jobs=[job1, job2],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_worker() -> Worker:
    """Create a sample worker for testing"""
    return Worker(
        id="test-worker-1",
        status=WorkerStatus.IDLE,
        capabilities=[JobType.VALIDATION, JobType.PROCESSING],
        last_heartbeat=datetime.now(UTC),
        registered_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_job() -> Job:
    """Create a sample job for testing"""
    return Job(
        id="redis-job-1",
        type=JobType.PROCESSING,
        parameters={"process": "data"},
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
