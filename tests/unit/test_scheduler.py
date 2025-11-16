"""Unit tests for Scheduler"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Callable

from coordinator.core.scheduler import Scheduler
from coordinator.core.state_manager import StateManager
from shared.enums import JobType, WorkerStatus
from shared.models import Worker


@pytest.mark.unit
@pytest.mark.asyncio
class TestScheduler:
    """Test Scheduler job assignment logic"""

    @pytest.fixture
    def scheduler(self, state_manager: StateManager) -> Scheduler:
        """Create a Scheduler instance"""
        return Scheduler(state_manager)

    async def test_send_message_success(self, scheduler: Scheduler,
                                        state_manager: StateManager,
                                        mock_websocket: MagicMock) -> None:
        """Test sending message to connected worker"""
        state_manager.active_connections["worker-1"] = mock_websocket

        result = await scheduler.send_message("worker-1", {"type": "test"})

        assert result is True
        mock_websocket.send_json.assert_called_once()

    async def test_send_message_worker_not_connected(
            self, scheduler: Scheduler) -> None:
        """Test sending message to disconnected worker"""
        result = await scheduler.send_message("nonexistent", {"type": "test"})

        assert result is False

    async def test_assign_job_success(self, scheduler: Scheduler,
                                      state_manager: StateManager,
                                      worker_factory: Callable[..., Worker],
                                      mock_websocket: MagicMock) -> None:
        """Test successful job assignment"""
        # Setup worker
        worker = worker_factory(worker_id="worker-1",
                                capabilities=[JobType.VALIDATION],
                                status=WorkerStatus.IDLE)
        state_manager.add_worker(worker)
        state_manager.active_connections["worker-1"] = mock_websocket

        # Assign job
        result = await scheduler.assign_job("job-1", JobType.VALIDATION,
                                            {"test": "data"})

        assert result == "worker-1"
        assert state_manager.get_job_worker("job-1") == "worker-1"
        assert worker.status == WorkerStatus.BUSY
        assert worker.current_job_id == "job-1"

    async def test_assign_job_no_suitable_worker(
            self, scheduler: Scheduler, state_manager: StateManager,
            worker_factory: Callable[..., Worker]) -> None:
        """Test job assignment when no suitable worker is available"""
        # Setup worker with different capability
        worker = worker_factory(worker_id="worker-1",
                                capabilities=[JobType.PROCESSING],
                                status=WorkerStatus.IDLE)
        state_manager.add_worker(worker)

        # Try to assign validation job
        result = await scheduler.assign_job("job-1", JobType.VALIDATION,
                                            {"test": "data"})

        assert result is None

    async def test_assign_job_all_workers_busy(
            self, scheduler: Scheduler, state_manager: StateManager,
            worker_factory: Callable[..., Worker]) -> None:
        """Test job assignment when all workers are busy"""
        worker = worker_factory(
            worker_id="worker-1",
            capabilities=[JobType.VALIDATION],
            status=WorkerStatus.BUSY  # Already busy
        )
        state_manager.add_worker(worker)

        result = await scheduler.assign_job("job-1", JobType.VALIDATION,
                                            {"test": "data"})

        assert result is None

    async def test_handle_job_completion(
            self, scheduler: Scheduler, state_manager: StateManager,
            worker_factory: Callable[..., Worker]) -> None:
        """Test handling job completion"""
        # Setup worker with assigned job
        worker = worker_factory(worker_id="worker-1",
                                status=WorkerStatus.BUSY,
                                current_job_id="job-1")
        state_manager.add_worker(worker)
        state_manager.assign_job("job-1", "worker-1")

        # Complete job
        await scheduler.handle_job_completion("worker-1", "job-1",
                                              {"result": "success"})

        assert worker.status == WorkerStatus.IDLE
        assert worker.current_job_id is None
        assert state_manager.get_job_worker("job-1") is None

    async def test_broadcast_message(self, scheduler: Scheduler,
                                     state_manager: StateManager,
                                     mock_websocket: MagicMock) -> None:
        """Test broadcasting message to all workers"""
        # Setup multiple workers
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        state_manager.active_connections["worker-1"] = ws1
        state_manager.active_connections["worker-2"] = ws2

        disconnected = await scheduler.broadcast({"type": "announcement"})

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        assert len(disconnected) == 0
