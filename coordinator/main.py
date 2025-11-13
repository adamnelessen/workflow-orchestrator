from fastapi import FastAPI
from datetime import datetime
import uvicorn

from coordinator.api import workflows, workers

app = FastAPI(
    title="Workflow Orchestrator - Coordinator",
    description="Coordinates workflow execution across distributed workers",
    version="0.1.0")

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
async def health():
    """Detailed health status"""
    from coordinator.core.storage import workflows as wf_storage, workers as worker_storage
    from shared.schemas import WorkerStatus

    return {
        "status":
        "healthy",
        "workflows":
        len(wf_storage),
        "workers":
        len(worker_storage),
        "active_workers":
        len([
            w for w in worker_storage.values()
            if w.status != WorkerStatus.OFFLINE
        ])
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
