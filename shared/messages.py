"""WebSocket message schemas for coordinator-worker communication"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

from .enums import MessageType


class WebSocketMessage(BaseModel):
    """Base schema for all WebSocket messages"""
    type: MessageType
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()})


# ============================================================================
# Worker -> Coordinator Messages
# ============================================================================


class RegisterMessage(WebSocketMessage):
    """Worker registration message"""
    type: MessageType = MessageType.REGISTER
    capabilities: List[str]  # Job type capabilities as strings


class HeartbeatMessage(WebSocketMessage):
    """Worker heartbeat message"""
    type: MessageType = MessageType.HEARTBEAT
    worker_id: Optional[str] = None


class JobStatusMessage(WebSocketMessage):
    """Job status update from worker"""
    type: MessageType = MessageType.JOB_STATUS
    job_id: str
    status: str  # JobStatus as string
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ReadyMessage(WebSocketMessage):
    """Worker ready for new jobs"""
    type: MessageType = MessageType.READY
    worker_id: Optional[str] = None


# ============================================================================
# Coordinator -> Worker Messages
# ============================================================================


class RegistrationAckMessage(WebSocketMessage):
    """Acknowledgment of worker registration"""
    type: MessageType = MessageType.REGISTRATION_ACK
    status: str = "registered"
    worker_id: str


class HeartbeatAckMessage(WebSocketMessage):
    """Acknowledgment of worker heartbeat"""
    type: MessageType = MessageType.HEARTBEAT_ACK


class JobAssignmentMessage(WebSocketMessage):
    """Job assignment to worker"""
    type: MessageType = MessageType.JOB_ASSIGNMENT
    job_id: str
    job_type: str  # JobType as string
    parameters: Dict[str, Any]
