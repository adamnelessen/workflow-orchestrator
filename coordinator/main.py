from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
from coordinator.core.state_manager import StateManager, state_manager
from coordinator.core.dependencies import get_worker_registry, get_workflow_engine
from coordinator.api import workflows, workers, health
from contextlib import asynccontextmanager
import asyncio
import logging
import os

# Use LOG_LEVEL from environment, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
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
app.include_router(health.router)
app.include_router(workflows.router)
app.include_router(workers.router)

if __name__ == "__main__":
    uvicorn.run("coordinator.main:app", host="0.0.0.0", port=8000, reload=True)
