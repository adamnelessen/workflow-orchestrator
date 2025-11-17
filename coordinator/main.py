from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from coordinator.core.dependencies import get_worker_registry, get_workflow_engine
from coordinator.core.state_manager import init_state_manager
from coordinator.api import workflows, workers, health, jobs
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
    # Initialize state manager with databases
    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL")

    if database_url or redis_url:
        logger.info(
            f"Initializing state manager with backends (DB: {bool(database_url)}, Redis: {bool(redis_url)})"
        )
        await init_state_manager(database_url=database_url,
                                 redis_url=redis_url)
    else:
        logger.info("Running with in-memory state only")

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
app.include_router(jobs.router)

if __name__ == "__main__":
    uvicorn.run("coordinator.main:app", host="0.0.0.0", port=8000, reload=True)
