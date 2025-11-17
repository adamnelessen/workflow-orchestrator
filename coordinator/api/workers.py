from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List
from datetime import datetime, UTC
import logging

from shared.models import Worker
from shared.enums import MessageType, JobStatus, WorkflowStatus
from shared.messages import (
    RegisterMessage,
    HeartbeatMessage,
    JobStatusMessage,
    ReadyMessage,
    RegistrationAckMessage,
    HeartbeatAckMessage,
)
from coordinator.core.state_manager import StateManager, state_manager
from coordinator.core.dependencies import get_worker_registry, get_workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("", response_model=List[Worker])
async def list_workers(state: StateManager = Depends(state_manager)):
    """List all workers"""
    return state.list_workers()


@router.websocket("/{worker_id}")
async def websocket_endpoint(websocket: WebSocket, worker_id: str):
    """WebSocket endpoint for worker connections."""
    # Note: WebSocket endpoints can't use Depends(), so we get dependencies directly
    state = state_manager()
    worker_registry = get_worker_registry()
    workflow_engine = get_workflow_engine()

    await worker_registry.connect(websocket, worker_id)

    try:
        while True:
            # Receive message from worker
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == MessageType.REGISTER.value:
                # Worker registration
                msg = RegisterMessage(**data)
                await worker_registry.register_worker(worker_id,
                                                      msg.capabilities)

                # Send acknowledgment
                ack = RegistrationAckMessage(worker_id=worker_id,
                                             timestamp=datetime.now(UTC))
                await websocket.send_json(ack.model_dump(mode='json'))

            elif message_type == MessageType.HEARTBEAT.value:
                # Worker heartbeat
                msg = HeartbeatMessage(**data)
                await worker_registry.handle_heartbeat(worker_id)

                ack = HeartbeatAckMessage(timestamp=datetime.now(UTC))
                await websocket.send_json(ack.model_dump(mode='json'))

            elif message_type == MessageType.JOB_STATUS.value:
                # Job status update from worker
                msg = JobStatusMessage(**data)

                if msg.status == JobStatus.COMPLETED.value:
                    await workflow_engine.handle_job_completion(
                        msg.job_id, msg.result or {})
                elif msg.status == JobStatus.FAILED.value:
                    await workflow_engine.handle_job_failure(
                        msg.job_id, msg.result or {})
                else:
                    workflow_engine.update_job_status(msg.job_id, msg.status)

                logger.info(f"Job {msg.job_id} status update: {msg.status}")

            elif message_type == MessageType.READY.value:
                # Worker is ready for new jobs
                msg = ReadyMessage(**data)
                worker = state.get_worker(worker_id)
                if worker is not None:
                    worker.status = "idle"

                    # Try to schedule any pending/retrying jobs that are waiting for workers
                    for workflow in state.list_workflows():
                        if workflow.status == WorkflowStatus.RUNNING:
                            await workflow_engine._reschedule_pending_jobs(
                                workflow)

            else:
                logger.warning(
                    f"Unknown message type from worker {worker_id}: {message_type}"
                )

    except WebSocketDisconnect:
        await worker_registry.disconnect(worker_id)
        logger.info(f"Worker {worker_id} disconnected")
    except Exception as e:
        logger.error(f"Error handling worker {worker_id}: {e}")
        await worker_registry.disconnect(worker_id)
