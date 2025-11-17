"""Domain model definitions for workflows, jobs, and workers"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from .enums import JobStatus, JobType, WorkflowStatus, WorkerStatus


class Job(BaseModel):
    """A unit of work to be executed by a worker"""
    id: str
    type: JobType
    parameters: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    on_success: Optional[List[str]] = None
    on_failure: Optional[List[str]] = None
    always_run: bool = False
    created_at: datetime
    updated_at: datetime


class Workflow(BaseModel):
    """A collection of jobs with dependencies"""
    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    jobs: List[Job]
    current_jobs: List[str] = []  # Currently executing job IDs
    completed_jobs: List[str] = []
    failed_jobs: List[str] = []
    created_at: datetime
    updated_at: datetime


class Worker(BaseModel):
    """A worker node that can execute jobs"""
    id: str
    status: WorkerStatus = WorkerStatus.IDLE
    capabilities: List[JobType]  # Which job types this worker can handle
    current_job_id: Optional[str] = None
    last_heartbeat: datetime
    registered_at: datetime
