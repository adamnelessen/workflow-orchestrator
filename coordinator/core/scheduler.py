import logging
from typing import Optional
from datetime import datetime, UTC
from fastapi import WebSocket
from coordinator.core.state_manager import StateManager
from shared.messages import JobAssignmentMessage

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for assigning jobs to workers."""

    def __init__(self, state: StateManager):
        self.state = state

    async def send_message(self, worker_id: str, message: dict):
        """Send a message to a specific worker."""
        if worker_id in self.state.active_connections:
            websocket: WebSocket = self.state.active_connections[worker_id]
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(
                    f"Error sending message to worker {worker_id}: {e}")
                return False
        return False

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected workers."""
        disconnected = []
        for worker_id, websocket in self.state.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to worker {worker_id}: {e}")
                disconnected.append(worker_id)

        # Return list of disconnected workers for caller to handle
        return disconnected

    async def assign_job(self, job_id: str, job_type: str,
                         parameters: dict) -> Optional[str]:
        """Assign a job to an available worker with matching capabilities."""
        suitable_workers = [
            worker_id for worker_id, worker in self.state.workers.items()
            if job_type in worker.capabilities and worker.status == "idle"
        ]

        if not suitable_workers:
            logger.warning(
                f"No suitable workers available for job type: {job_type}")
            return None

        # Simple round-robin selection (can be improved with load balancing)
        worker_id = suitable_workers[0]
        worker = await self.state.get_worker(worker_id)

        if worker is None:
            return None

        # Update worker status
        worker.status = "busy"
        worker.current_job_id = job_id
        await self.state.assign_job(job_id, worker_id)

        # Send job to worker
        message = JobAssignmentMessage(job_id=job_id,
                                       job_type=job_type,
                                       parameters=parameters,
                                       timestamp=datetime.now(UTC))

        success = await self.send_message(worker_id,
                                          message.model_dump(mode='json'))
        if success:
            logger.info(f"Job {job_id} assigned to worker {worker_id}")
            return worker_id
        else:
            # Revert status if sending failed
            worker.status = "idle"
            worker.current_job_id = None
            await self.state.unassign_job(job_id)
            return None

    async def handle_job_completion(self, worker_id: str, job_id: str,
                                    result: dict):
        """Handle job completion from a worker."""
        worker = await self.state.get_worker(worker_id)
        if worker is not None:
            worker.status = "idle"
            worker.current_job_id = None

        await self.state.unassign_job(job_id)

        logger.info(f"Job {job_id} completed by worker {worker_id}")
