from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from shared.schemas import Worker
from coordinator.core.storage import workers

router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("", response_model=Worker)
async def register_worker(worker: Worker):
    """Register a new worker"""
    worker.registered_at = datetime.now()
    worker.last_heartbeat = datetime.now()
    workers[worker.id] = worker
    return worker


@router.get("", response_model=List[Worker])
async def list_workers():
    """List all workers"""
    return list(workers.values())


@router.post("/{worker_id}/heartbeat")
async def worker_heartbeat(worker_id: str):
    """Update worker heartbeat"""
    if worker_id not in workers:
        raise HTTPException(status_code=404, detail="Worker not found")

    workers[worker_id].last_heartbeat = datetime.now()
    return {"message": "Heartbeat received"}
