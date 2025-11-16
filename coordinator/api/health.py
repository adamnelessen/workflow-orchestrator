"""Health check and status endpoints"""
from fastapi import APIRouter, Depends
from datetime import datetime, UTC

from coordinator.core.state_manager import StateManager, state_manager
from shared.enums import WorkerStatus

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "coordinator",
        "status": "running",
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.get("/health")
async def health(state: StateManager = Depends(state_manager)):
    """Detailed health status"""
    return {
        "status":
        "healthy",
        "workflows":
        len(state.workflows),
        "workers":
        len(state.workers),
        "active_workers":
        len([
            w for w in state.workers.values()
            if w.status != WorkerStatus.OFFLINE
        ])
    }
