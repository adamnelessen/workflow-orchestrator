"""Unit tests for WorkerRegistry"""
import pytest
from datetime import datetime, UTC, timedelta
from typing import Callable
from unittest.mock import MagicMock

from coordinator.core.worker_registry import WorkerRegistry
from coordinator.core.state_manager import StateManager
from shared.enums import JobType, WorkerStatus
from shared.models import Worker


@pytest.mark.unit
@pytest.mark.asyncio
class TestWorkerRegistry:
    """Test WorkerRegistry operations"""

    @pytest.fixture
    def registry(self, state_manager: StateManager) -> WorkerRegistry:
        """Create a WorkerRegistry instance"""
        return WorkerRegistry(state_manager)

    async def test_connect_worker(self, registry: WorkerRegistry,
                                  state_manager: StateManager,
                                  mock_websocket: MagicMock) -> None:
        """Test accepting worker connection"""
        await registry.connect(mock_websocket, "worker-1")

        assert "worker-1" in state_manager.active_connections
        mock_websocket.accept.assert_called_once()

    async def test_disconnect_worker(self, registry: WorkerRegistry,
                                     state_manager: StateManager,
                                     mock_websocket: MagicMock) -> None:
        """Test worker disconnection"""
        # Connect first
        state_manager.active_connections["worker-1"] = mock_websocket
        worker = await state_manager.get_worker("worker-1")
        if worker:
            await state_manager.add_worker(worker)

        # Disconnect
        await registry.disconnect("worker-1")

        assert "worker-1" not in state_manager.active_connections

    async def test_register_worker(self, registry: WorkerRegistry,
                                   state_manager: StateManager) -> None:
        """Test worker registration"""
        capabilities = [JobType.VALIDATION, JobType.PROCESSING]

        await registry.register_worker("worker-1", capabilities)

        worker = await state_manager.get_worker("worker-1")
        assert worker is not None
        assert worker.id == "worker-1"
        assert worker.capabilities == capabilities

    async def test_handle_heartbeat(
            self, registry: WorkerRegistry, state_manager: StateManager,
            worker_factory: Callable[..., Worker]) -> None:
        """Test heartbeat handling"""
        # Setup worker
        worker = worker_factory(worker_id="worker-1")
        old_heartbeat = worker.last_heartbeat
        await state_manager.add_worker(worker)

        # Wait a moment and send heartbeat
        import asyncio
        await asyncio.sleep(0.01)
        await registry.handle_heartbeat("worker-1")

        # Check heartbeat updated
        updated_worker = await state_manager.get_worker("worker-1")
        assert updated_worker.last_heartbeat > old_heartbeat

    async def test_handle_heartbeat_nonexistent_worker(
            self, registry: WorkerRegistry) -> None:
        """Test heartbeat for worker that doesn't exist"""
        # Should not raise error
        await registry.handle_heartbeat("nonexistent")


@pytest.mark.unit
class TestWorkerRegistryHealthCheck:
    """Test worker health check functionality"""

    def test_worker_appears_healthy(
            self, worker_factory: Callable[..., Worker]) -> None:
        """Test that recently heartbeated worker is healthy"""
        worker = worker_factory()
        worker.last_heartbeat = datetime.now(UTC)

        time_since = (datetime.now(UTC) - worker.last_heartbeat).seconds
        assert time_since < 60

    def test_worker_appears_unhealthy(
            self, worker_factory: Callable[..., Worker]) -> None:
        """Test that stale worker appears unhealthy"""
        worker = worker_factory()
        worker.last_heartbeat = datetime.now(UTC) - timedelta(seconds=120)

        time_since = (datetime.now(UTC) - worker.last_heartbeat).seconds
        assert time_since > 60
