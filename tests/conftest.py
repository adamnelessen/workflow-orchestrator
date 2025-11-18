"""Root conftest.py - Shared fixtures for all tests"""
import pytest
import os
from datetime import datetime, UTC
from typing import Callable, Any, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

from coordinator.core.state_manager import StateManager
from shared.enums import JobType, JobStatus, WorkflowStatus, WorkerStatus
from shared.models import Job, Workflow, Worker

# ============================================================================
# Pytest Configuration
# ============================================================================

# Note: pytest-asyncio handles event loop creation automatically
# The custom event_loop fixture has been removed to avoid deprecation warnings

# ============================================================================
# Database Fixtures (for integration tests)
# ============================================================================


@pytest.fixture
async def postgres_db() -> AsyncGenerator:
    """Create a test database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set - skipping PostgreSQL tests")
    
    from coordinator.db.postgres import PostgresDB
    db = PostgresDB(database_url)
    await db.init_db()
    yield db
    await db.close()


@pytest.fixture
async def redis_cache() -> AsyncGenerator:
    """Create a test Redis connection"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set - skipping Redis tests")
    
    from coordinator.db.redis import RedisCache
    cache = RedisCache(redis_url)
    await cache.connect()
    yield cache
    await cache.close()


@pytest.fixture
async def full_state_manager() -> AsyncGenerator:
    """Create StateManager with full database stack"""
    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL")
    
    if not (database_url and redis_url):
        pytest.skip("DATABASE_URL or REDIS_URL not set - skipping full stack tests")
    
    from coordinator.core.state_manager import init_state_manager
    state = await init_state_manager(database_url, redis_url)
    yield state
    
    # Cleanup
    if state.postgres:
        await state.postgres.close()
    if state.redis:
        await state.redis.close()


# ============================================================================
# Data Factories
# ============================================================================


@pytest.fixture
def job_factory() -> Callable:
    """Factory for creating test Job instances"""

    def _create_job(job_id: str = "test-job-1",
                    job_type: JobType = JobType.VALIDATION,
                    parameters: dict | None = None,
                    status: JobStatus = JobStatus.PENDING,
                    **kwargs) -> Job:
        return Job(id=job_id,
                   type=job_type,
                   parameters=parameters or {"test": "data"},
                   status=status,
                   created_at=datetime.now(UTC),
                   updated_at=datetime.now(UTC),
                   **kwargs)

    return _create_job


@pytest.fixture
def workflow_factory(job_factory: Callable) -> Callable:
    """Factory for creating test Workflow instances"""

    def _create_workflow(workflow_id: str = "test-workflow-1",
                         name: str = "Test Workflow",
                         jobs: list[Job] | None = None,
                         status: WorkflowStatus = WorkflowStatus.PENDING,
                         **kwargs) -> Workflow:
        if jobs is None:
            jobs = [
                job_factory(job_id=f"{workflow_id}-job-1"),
                job_factory(job_id=f"{workflow_id}-job-2",
                            job_type=JobType.PROCESSING)
            ]

        return Workflow(id=workflow_id,
                        name=name,
                        jobs=jobs,
                        status=status,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                        **kwargs)

    return _create_workflow


@pytest.fixture
def worker_factory() -> Callable:
    """Factory for creating test Worker instances"""

    def _create_worker(worker_id: str = "test-worker-1",
                       host: str = "localhost",
                       port: int = 9000,
                       capabilities: list[JobType] | None = None,
                       status: WorkerStatus = WorkerStatus.IDLE,
                       **kwargs) -> Worker:
        if capabilities is None:
            capabilities = [JobType.VALIDATION, JobType.PROCESSING]

        return Worker(id=worker_id,
                      host=host,
                      port=port,
                      capabilities=capabilities,
                      status=status,
                      last_heartbeat=datetime.now(UTC),
                      registered_at=datetime.now(UTC),
                      **kwargs)

    return _create_worker


# ============================================================================
# Component Fixtures
# ============================================================================


@pytest.fixture
def state_manager() -> StateManager:
    """Create a fresh StateManager instance for testing"""
    return StateManager()


@pytest.fixture
def scheduler(state_manager: StateManager):
    """Create a scheduler for testing"""
    from coordinator.core.scheduler import Scheduler
    return Scheduler(state_manager)


@pytest.fixture
def workflow_engine(state_manager: StateManager, scheduler):
    """Create a workflow engine for testing"""
    from coordinator.core.workflow_engine import WorkflowEngine
    return WorkflowEngine(state_manager, scheduler)


@pytest.fixture
def simple_workflow() -> Workflow:
    """Create a simple linear workflow"""
    now = datetime.now(UTC)
    jobs = [
        Job(id="job1",
            type=JobType.VALIDATION,
            parameters={"check": "prerequisites"},
            status=JobStatus.PENDING,
            on_success=["job2"],
            created_at=now,
            updated_at=now),
        Job(id="job2",
            type=JobType.PROCESSING,
            parameters={"operation": "execute"},
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now),
    ]
    workflow = Workflow(id="workflow1",
                        name="simple-workflow",
                        status=WorkflowStatus.PENDING,
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)
    return workflow


@pytest.fixture
def branching_workflow() -> Workflow:
    """Create a workflow with success/failure branches"""
    now = datetime.now(UTC)
    jobs = [
        Job(id="job1",
            type=JobType.VALIDATION,
            parameters={},
            status=JobStatus.PENDING,
            on_success=["job2"],
            on_failure=["job3"],
            created_at=now,
            updated_at=now),
        Job(id="job2",
            type=JobType.PROCESSING,
            parameters={},
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now),
        Job(id="job3",
            type=JobType.CLEANUP,
            parameters={},
            status=JobStatus.PENDING,
            always_run=True,
            created_at=now,
            updated_at=now),
    ]
    workflow = Workflow(id="workflow2",
                        name="branching-workflow",
                        status=WorkflowStatus.PENDING,
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)
    return workflow


@pytest.fixture
def mock_worker(state_manager: StateManager) -> Worker:
    """Create a mock worker"""
    import asyncio
    now = datetime.now(UTC)
    worker = Worker(
        id="worker1",
        status=WorkerStatus.IDLE,
        capabilities=[JobType.VALIDATION, JobType.PROCESSING, JobType.CLEANUP],
        last_heartbeat=now,
        registered_at=now)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(state_manager.add_worker(worker))
    return worker


@pytest.fixture
def populated_state(state_manager: StateManager, workflow_factory: Callable,
                    worker_factory: Callable) -> StateManager:
    """StateManager with pre-populated test data"""
    # We need to run this asynchronously, but fixtures can't be async in this context
    # So we'll use asyncio.get_event_loop().run_until_complete
    import asyncio
    
    async def populate():
        # Add workflows
        workflow1 = workflow_factory(workflow_id="wf-1", name="Workflow 1")
        workflow2 = workflow_factory(workflow_id="wf-2", name="Workflow 2")
        await state_manager.add_workflow(workflow1)
        await state_manager.add_workflow(workflow2)

        # Add workers
        worker1 = worker_factory(worker_id="worker-1", port=9001)
        worker2 = worker_factory(worker_id="worker-2", port=9002)
        await state_manager.add_worker(worker1)
        await state_manager.add_worker(worker2)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(populate())
    return state_manager


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Mock WebSocket connection"""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(return_value={"type": "heartbeat"})
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_worker_registry(state_manager: StateManager):
    """Mock WorkerRegistry for testing"""
    from coordinator.core.worker_registry import WorkerRegistry
    registry = WorkerRegistry(state_manager)
    return registry


# ============================================================================
# Sample Test Data
# ============================================================================


@pytest.fixture
def sample_job_parameters() -> dict[JobType, dict[str, Any]]:
    """Sample job parameters for different job types"""
    return {
        JobType.VALIDATION: {
            "schema": "user_data",
            "strict": True
        },
        JobType.PROCESSING: {
            "batch_size": 100,
            "timeout": 300
        },
        JobType.INTEGRATION: {
            "endpoint": "https://api.example.com",
            "method": "POST"
        },
        JobType.CLEANUP: {
            "older_than_days": 30
        }
    }


@pytest.fixture
def sample_workflow_config() -> dict[str, Any]:
    """Sample workflow configuration"""
    now = datetime.now(UTC).isoformat()
    return {
        "name":
        "data-pipeline",
        "jobs": [{
            "id": "validate-1",
            "type": JobType.VALIDATION.value,
            "parameters": {
                "schema": "input"
            },
            "created_at": now,
            "updated_at": now
        }, {
            "id": "process-1",
            "type": JobType.PROCESSING.value,
            "parameters": {
                "batch_size": 50
            },
            "on_success": ["integrate-1"],
            "created_at": now,
            "updated_at": now
        }, {
            "id": "integrate-1",
            "type": JobType.INTEGRATION.value,
            "parameters": {
                "endpoint": "/api/data"
            },
            "created_at": now,
            "updated_at": now
        }]
    }


@pytest.fixture
def workflow_with_jobs(
        sample_job_parameters: dict[JobType, dict[str, Any]]) -> Callable:
    """Create a workflow with jobs for testing
    
    Returns a function that accepts a TestClient and creates a workflow.
    This allows the fixture to work with the client fixture from individual test files.
    """

    def _create_workflow(client) -> dict[str, Any]:
        from fastapi.testclient import TestClient
        import uuid

        # Use unique ID for each workflow to avoid conflicts between tests
        workflow_id = f"wf-test-{uuid.uuid4().hex[:8]}"

        workflow_data = {
            "id":
            workflow_id,
            "name":
            "Test Pipeline",
            "jobs": [{
                "id": "job-1",
                "type": JobType.VALIDATION.value,
                "parameters": sample_job_parameters[JobType.VALIDATION],
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }, {
                "id": "job-2",
                "type": JobType.PROCESSING.value,
                "parameters": sample_job_parameters[JobType.PROCESSING],
                "on_success": ["job-3"],
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }, {
                "id": "job-3",
                "type": JobType.INTEGRATION.value,
                "parameters": sample_job_parameters[JobType.INTEGRATION],
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }],
            "created_at":
            datetime.now(UTC).isoformat(),
            "updated_at":
            datetime.now(UTC).isoformat()
        }

        response = client.post("/workflows", json=workflow_data)
        assert response.status_code == 200
        return response.json()

    return _create_workflow
