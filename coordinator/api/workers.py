from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from typing import List
from datetime import datetime, UTC
import logging

from shared.schemas import Worker
from coordinator.core.state_manager import StateManager, state_manager
from coordinator.core.dependencies import get_worker_registry
from coordinator.core.workflow_engine import get_workflow_engine

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
    ws_manager = get_worker_registry()
    workflow_engine = get_workflow_engine()

    await ws_manager.connect(websocket, worker_id)

    try:
        while True:
            # Receive message from worker
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "register":
                # Worker registration
                capabilities = data.get("capabilities", [])
                await ws_manager.register_worker(worker_id, capabilities)

                # Send acknowledgment
                await websocket.send_json({
                    "type": "registration_ack",
                    "status": "registered",
                    "worker_id": worker_id
                })

            elif message_type == "heartbeat":
                # Worker heartbeat
                await ws_manager.handle_heartbeat(worker_id)
                await websocket.send_json({
                    "type":
                    "heartbeat_ack",
                    "timestamp":
                    datetime.now(UTC).isoformat()
                })

            elif message_type == "job_status":
                # Job status update from worker
                job_id = data.get("job_id")
                status = data.get("status")
                result = data.get("result", {})

                if status == "completed":
                    await ws_manager.handle_job_completion(
                        worker_id, job_id, result)
                    await workflow_engine.handle_job_completion(job_id, result)
                elif status == "failed":
                    await ws_manager.handle_job_completion(
                        worker_id, job_id, result)
                    await workflow_engine.handle_job_failure(job_id, result)
                else:
                    await workflow_engine.update_job_status(job_id, status)

                logger.info(f"Job {job_id} status update: {status}")

            elif message_type == "ready":
                # Worker is ready for new jobs
                worker = state.get_worker(worker_id)
                if worker is not None:
                    worker.status = "idle"

            else:
                logger.warning(
                    f"Unknown message type from worker {worker_id}: {message_type}"
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(worker_id)
        logger.info(f"Worker {worker_id} disconnected")
    except Exception as e:
        logger.error(f"Error handling worker {worker_id}: {e}")
        await ws_manager.disconnect(worker_id)
