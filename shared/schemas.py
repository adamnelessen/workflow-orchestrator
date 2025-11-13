from pydantic import BaseModel
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, Enum):
    VALIDATION = "validation"
    PROCESSING = "processing"
    INTEGRATION = "integration"
    CLEANUP = "cleanup"


class Job(BaseModel):
    id: str
    type: JobType
    parameters: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    always_run: bool = False
    created_at: datetime
    updated_at: datetime


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(BaseModel):
    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    jobs: List[Job]
    current_jobs: List[str] = []  # Currently executing job IDs
    completed_jobs: List[str] = []
    failed_jobs: List[str] = []
    created_at: datetime
    updated_at: datetime


class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class Worker(BaseModel):
    id: str
    host: str
    port: int
    status: WorkerStatus = WorkerStatus.IDLE
    capabilities: List[JobType]  # Which job types this worker can handle
    current_job_id: Optional[str] = None
    last_heartbeat: datetime
    registered_at: datetime
