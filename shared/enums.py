"""Enum definitions for the workflow orchestrator"""
from enum import Enum


class JobStatus(str, Enum):
    """Status values for job execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class JobType(str, Enum):
    """Types of jobs that can be executed"""
    VALIDATION = "validation"
    PROCESSING = "processing"
    INTEGRATION = "integration"
    CLEANUP = "cleanup"


class WorkflowStatus(str, Enum):
    """Status values for workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerStatus(str, Enum):
    """Status values for worker availability"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class MessageType(str, Enum):
    """Types of messages exchanged between coordinator and workers"""
    # Worker -> Coordinator
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    JOB_STATUS = "job_status"
    READY = "ready"

    # Coordinator -> Worker
    REGISTRATION_ACK = "registration_ack"
    HEARTBEAT_ACK = "heartbeat_ack"
    JOB_ASSIGNMENT = "job_assignment"
