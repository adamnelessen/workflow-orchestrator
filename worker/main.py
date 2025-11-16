"""Worker node that connects to coordinator via WebSocket."""
import asyncio
import json
import logging
import os
import signal
import uuid
from typing import List, Optional
from datetime import datetime, UTC
from worker.jobs import validation, processing, integration, cleanup
import websockets
from websockets.exceptions import ConnectionClosed

from shared.enums import MessageType, JobStatus, JobType
from shared.messages import (
    RegisterMessage,
    HeartbeatMessage,
    JobStatusMessage,
    ReadyMessage,
    RegistrationAckMessage,
    JobAssignmentMessage,
)

# Use LOG_LEVEL from environment, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)


class WorkerNode:
    """Worker node that executes jobs from the coordinator."""

    def __init__(self,
                 worker_id: Optional[str] = None,
                 capabilities: Optional[List[str]] = None):
        """Initialize worker node."""
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.capabilities = capabilities or [
            "validation", "processing", "integration", "cleanup"
        ]
        self.coordinator_url = os.getenv("COORDINATOR_URL",
                                         "ws://coordinator:8000/workers")
        self.websocket = None
        self.running = True
        self.current_job = None

    async def connect(self):
        """Connect to the coordinator via WebSocket."""
        url = f"{self.coordinator_url}/{self.worker_id}"
        logger.info(f"Connecting to coordinator at {url}")

        try:
            self.websocket = await websockets.connect(url)
            logger.info(f"Connected to coordinator as {self.worker_id}")

            # Register with coordinator
            await self.register()

            # Start heartbeat task
            asyncio.create_task(self.send_heartbeat())

            return True
        except Exception as e:
            logger.error(f"Failed to connect to coordinator: {e}")
            return False

    async def register(self):
        """Register capabilities with the coordinator."""
        message = RegisterMessage(capabilities=self.capabilities,
                                  timestamp=datetime.now(UTC))
        await self.websocket.send(message.model_dump_json())
        logger.info(f"Registered with capabilities: {self.capabilities}")

    async def send_heartbeat(self):
        """Send periodic heartbeat to coordinator."""
        while self.running and self.websocket:
            try:
                message = HeartbeatMessage(worker_id=self.worker_id,
                                           timestamp=datetime.now(UTC))
                await self.websocket.send(message.model_dump_json())
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                break

    async def execute_job(self, job_id: str, job_type: str, parameters: dict):
        """Execute a job based on its type."""
        logger.info(f"Executing job {job_id} of type {job_type}")
        self.current_job = job_id

        # Send status update - job started
        await self.send_job_status(job_id, JobStatus.RUNNING.value)

        try:
            result = None

            if job_type == JobType.VALIDATION.value:
                job = validation.Validation(parameters)
                result = await job.execute()
            elif job_type == JobType.PROCESSING.value:
                job = processing.Processing(parameters)
                result = await job.execute()
            elif job_type == JobType.INTEGRATION.value:
                job = integration.Integration(parameters)
                result = await job.execute()
            elif job_type == JobType.CLEANUP.value:
                job = cleanup.Cleanup(parameters)
                result = await job.execute()
            else:
                raise ValueError(f"Unknown job type: {job_type}")

            # Send completion status
            await self.send_job_status(job_id, JobStatus.COMPLETED.value,
                                       result)
            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self.send_job_status(job_id, JobStatus.FAILED.value,
                                       {"error": str(e)})
        finally:
            self.current_job = None
            # Notify coordinator that worker is ready for new jobs
            await self.send_ready_status()

    async def send_job_status(self,
                              job_id: str,
                              status: str,
                              result: Optional[dict] = None):
        """Send job status update to coordinator."""
        message = JobStatusMessage(job_id=job_id,
                                   status=status,
                                   worker_id=self.worker_id,
                                   result=result,
                                   timestamp=datetime.now(UTC))
        await self.websocket.send(message.model_dump_json())

    async def send_ready_status(self):
        """Notify coordinator that worker is ready for new jobs."""
        message = ReadyMessage(worker_id=self.worker_id,
                               timestamp=datetime.now(UTC))
        await self.websocket.send(message.model_dump_json())

    async def handle_message(self, message: dict):
        """Handle messages from the coordinator."""
        message_type = message.get("type")

        if message_type == MessageType.JOB_ASSIGNMENT.value:
            msg = JobAssignmentMessage(**message)
            # Execute job in background
            asyncio.create_task(
                self.execute_job(msg.job_id, msg.job_type, msg.parameters))

        elif message_type == MessageType.HEARTBEAT_ACK.value:
            # Heartbeat acknowledged
            pass

        elif message_type == MessageType.REGISTRATION_ACK.value:
            msg = RegistrationAckMessage(**message)
            logger.info(
                f"Registration acknowledged by coordinator: {msg.status}")

        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def run(self):
        """Main worker loop."""
        # Try to connect with retries
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries and self.running:
            if await self.connect():
                break
            retry_count += 1
            logger.info(
                f"Retrying connection ({retry_count}/{max_retries})...")
            await asyncio.sleep(5)

        if not self.websocket:
            logger.error("Failed to connect to coordinator")
            return

        try:
            # Main message loop
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except ConnectionClosed:
            logger.info("Connection to coordinator closed")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down worker...")
        self.running = False

        if self.websocket:
            await self.websocket.close()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(worker.shutdown())


async def main():
    """Main entry point."""
    global worker

    # Get configuration from environment
    worker_id = os.getenv("WORKER_ID", None)
    capabilities = os.getenv(
        "WORKER_CAPABILITIES",
        "validation,processing,integration,cleanup").split(",")

    # Create and run worker
    worker = WorkerNode(worker_id=worker_id, capabilities=capabilities)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
