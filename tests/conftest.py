"""Root conftest.py - Shared fixtures for all tests"""
import pytest
import asyncio
from datetime import datetime, UTC
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

from coordinator.core.state_manager import StateManager
from shared.schemas import (Job, JobType, JobStatus, Workflow, WorkflowStatus,
                            Worker, WorkerStatus)

# ============================================================================
# Pytest Configuration
# ============================================================================

# Note: pytest-asyncio handles event loop creation automatically
# The custom event_loop fixture has been removed to avoid deprecation warnings

# ============================================================================
# Data Factories
# ============================================================================


@pytest.fixture
def job_factory():
    """Factory for creating test Job instances"""

    def _create_job(job_id: str = "test-job-1",
                    job_type: JobType = JobType.VALIDATION,
                    parameters: dict = None,
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
def workflow_factory(job_factory):
    """Factory for creating test Workflow instances"""

    def _create_workflow(workflow_id: str = "test-workflow-1",
                         name: str = "Test Workflow",
                         jobs: list = None,
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
def worker_factory():
    """Factory for creating test Worker instances"""

    def _create_worker(worker_id: str = "test-worker-1",
                       host: str = "localhost",
                       port: int = 9000,
                       capabilities: list = None,
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
def state_manager():
    """Create a fresh StateManager instance for testing"""
    return StateManager()


@pytest.fixture
def populated_state(state_manager, workflow_factory, worker_factory):
    """StateManager with pre-populated test data"""
    # Add workflows
    workflow1 = workflow_factory(workflow_id="wf-1", name="Workflow 1")
    workflow2 = workflow_factory(workflow_id="wf-2", name="Workflow 2")
    state_manager.add_workflow(workflow1)
    state_manager.add_workflow(workflow2)

    # Add workers
    worker1 = worker_factory(worker_id="worker-1", port=9001)
    worker2 = worker_factory(worker_id="worker-2", port=9002)
    state_manager.add_worker(worker1)
    state_manager.add_worker(worker2)

    return state_manager


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(return_value={"type": "heartbeat"})
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_worker_registry(state_manager):
    """Mock WorkerRegistry for testing"""
    from coordinator.core.worker_registry import WorkerRegistry
    registry = WorkerRegistry(state_manager)
    return registry


# ============================================================================
# Sample Test Data
# ============================================================================


@pytest.fixture
def sample_job_parameters():
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
def sample_workflow_config():
    """Sample workflow configuration"""
    now = datetime.now(UTC).isoformat()
    return {
        "name":
        "data-pipeline",
        "jobs": [{
            "id": "validate-1",
            "type": JobType.VALIDATION,
            "parameters": {
                "schema": "input"
            },
            "created_at": now,
            "updated_at": now
        }, {
            "id": "process-1",
            "type": JobType.PROCESSING,
            "parameters": {
                "batch_size": 50
            },
            "on_success": "integrate-1",
            "created_at": now,
            "updated_at": now
        }, {
            "id": "integrate-1",
            "type": JobType.INTEGRATION,
            "parameters": {
                "endpoint": "/api/data"
            },
            "created_at": now,
            "updated_at": now
        }]
    }
