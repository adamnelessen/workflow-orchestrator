import asyncio
import logging
from datetime import datetime, UTC
from fastapi import WebSocket
from shared.models import Worker
from shared.enums import JobType
from coordinator.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class WorkerRegistry:
    """Manages WebSocket connections to worker nodes."""

    def __init__(self, state: StateManager):
        self.state = state

    async def connect(self, websocket: WebSocket, worker_id: str):
        """Accept a new worker connection."""
        await websocket.accept()
        self.state.active_connections[worker_id] = websocket
        logger.info(f"Worker {worker_id} connected via WebSocket")

    async def disconnect(self, worker_id: str):
        """Handle worker disconnection."""
        if worker_id in self.state.active_connections:
            del self.state.active_connections[worker_id]

        self.state.remove_worker(worker_id)
        logger.info(f"Worker {worker_id} disconnected")

        # Handle reassignment of jobs from disconnected worker
        await self._handle_worker_failure(worker_id)

    async def register_worker(self, worker_id: str,
                              capabilities: list[JobType]):
        """Register a worker with its capabilities."""
        worker = Worker(id=worker_id,
                        capabilities=capabilities,
                        last_heartbeat=datetime.now(UTC),
                        registered_at=datetime.now(UTC))
        self.state.add_worker(worker)
        logger.info(
            f"Worker {worker_id} registered with capabilities: {capabilities}")

    async def handle_heartbeat(self, worker_id: str):
        """Update worker's last heartbeat time."""
        worker = self.state.get_worker(worker_id)
        if worker is not None:
            worker.last_heartbeat = datetime.now(UTC)

    async def check_worker_health(self):
        """Periodic health check for workers."""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            current_time = datetime.now(UTC)

            for worker_id, worker in list(self.state.workers.items()):
                time_since_heartbeat = (current_time -
                                        worker.last_heartbeat).seconds
                if time_since_heartbeat > 60:  # No heartbeat for 60 seconds
                    logger.warning(
                        f"Worker {worker_id} appears to be unresponsive")
                    await self.disconnect(worker_id)

    async def _handle_worker_failure(self, worker_id: str):
        """Handle reassignment of jobs from a failed worker."""
        # Find jobs assigned to the failed worker
        failed_jobs = [
            job_id
            for job_id, assigned_worker in self.state.job_assignments.items()
            if assigned_worker == worker_id
        ]

        for job_id in failed_jobs:
            self.state.unassign_job(job_id)
            # Add job back to pending queue for reassignment
            # (Implementation depends on your job queue structure)
            logger.warning(
                f"Job {job_id} needs reassignment due to worker {worker_id} failure"
            )
