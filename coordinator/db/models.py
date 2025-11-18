"""SQLAlchemy ORM models for persistent storage"""
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import declarative_base
from shared.enums import JobStatus, JobType, WorkflowStatus, WorkerStatus

Base = declarative_base()


class WorkflowModel(Base):
    """Persistent workflow storage"""
    __tablename__ = "workflows"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(SQLEnum(WorkflowStatus), nullable=False)
    current_jobs = Column(JSON, default=list)  # List of job IDs
    completed_jobs = Column(JSON, default=list)
    failed_jobs = Column(JSON, default=list)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class JobModel(Base):
    """Persistent job storage"""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    workflow_id = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(JobType), nullable=False)
    parameters = Column(JSON, nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False)
    worker_id = Column(String, nullable=True, index=True)
    result = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    on_success = Column(JSON, nullable=True)  # List of job IDs
    on_failure = Column(JSON, nullable=True)  # List of job IDs
    always_run = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class WorkerModel(Base):
    """Persistent worker registry"""
    __tablename__ = "workers"

    id = Column(String, primary_key=True)
    status = Column(SQLEnum(WorkerStatus), nullable=False)
    capabilities = Column(JSON, nullable=False)  # List of JobType
    current_job_id = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=False)
    registered_at = Column(DateTime, nullable=False)


class JobAssignmentModel(Base):
    """Track job-to-worker assignments"""
    __tablename__ = "job_assignments"

    job_id = Column(String, primary_key=True)
    worker_id = Column(String, nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.now(UTC))
