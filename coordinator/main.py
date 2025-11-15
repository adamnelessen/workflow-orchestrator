from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
from coordinator.core.state_manager import StateManager, state_manager
from coordinator.core.dependencies import get_worker_registry, get_workflow_engine
from coordinator.api import workflows, workers
from contextlib import asynccontextmanager
import asyncio
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Initialize dependencies
    worker_registry = get_worker_registry()

    # Start background tasks
    health_check_task = asyncio.create_task(
        worker_registry.check_worker_health())
    logger.info("Coordinator started - WebSocket server ready")

    yield

    # Cleanup
    health_check_task.cancel()
    logger.info("Coordinator shutting down")


app = FastAPI(
    title="Workflow Orchestrator - Coordinator",
    description="Coordinates workflow execution across distributed workers",
    version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure workflow engine is initialized
get_workflow_engine()

# Include routers
app.include_router(workflows.router)
app.include_router(workers.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "coordinator",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health(state: StateManager = Depends(state_manager)):
    """Detailed health status"""
    from shared.schemas import WorkerStatus

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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
