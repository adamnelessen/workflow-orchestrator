"""Integration tests for Worker API endpoints and WebSocket connections"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, UTC

from coordinator.main import app
from shared.enums import WorkerStatus, JobType, JobStatus


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.mark.integration
class TestWorkerEndpoints:
    """Test worker REST API endpoints"""

    def test_list_workers(self, client: TestClient) -> None:
        """Test listing all workers"""
        response = client.get("/workers")

        assert response.status_code == 200
        workers = response.json()
        assert isinstance(workers, list)


@pytest.mark.integration
class TestWorkerWebSocket:
    """Test worker WebSocket functionality"""

    def test_websocket_registration(self) -> None:
        """Test worker registration via WebSocket"""
        client = TestClient(app)

        with client.websocket_connect("/workers/test-worker-reg") as websocket:
            # Send registration
            websocket.send_json({
                "type":
                "register",
                "capabilities":
                [JobType.VALIDATION.value, JobType.PROCESSING.value]
            })

            # Receive acknowledgment
            data = websocket.receive_json()
            assert data["type"] == "registration_ack"
            assert data["status"] == "registered"
            assert data["worker_id"] == "test-worker-reg"

    def test_websocket_heartbeat(self) -> None:
        """Test worker heartbeat via WebSocket"""
        client = TestClient(app)

        with client.websocket_connect("/workers/test-worker-hb") as websocket:
            # Register first
            websocket.send_json({
                "type": "register",
                "capabilities": [JobType.VALIDATION.value]
            })
            websocket.receive_json()  # Registration ack

            # Send heartbeat
            websocket.send_json({"type": "heartbeat"})

            # Receive heartbeat ack
            data = websocket.receive_json()
            assert data["type"] == "heartbeat_ack"
            assert "timestamp" in data

    def test_websocket_job_status_completed(self) -> None:
        """Test sending job completion status via WebSocket"""
        client = TestClient(app)

        with client.websocket_connect("/workers/test-worker-job") as websocket:
            # Register
            websocket.send_json({
                "type": "register",
                "capabilities": [JobType.VALIDATION.value]
            })
            websocket.receive_json()  # Registration ack

            # Send job completion
            websocket.send_json({
                "type": "job_status",
                "job_id": "job-123",
                "status": JobStatus.COMPLETED.value,
                "result": {
                    "success": True
                }
            })

            # Connection should stay open (no error/disconnect)

    def test_websocket_job_status_failed(self) -> None:
        """Test sending job failure status via WebSocket"""
        client = TestClient(app)

        with client.websocket_connect(
                "/workers/test-worker-fail") as websocket:
            # Register
            websocket.send_json({
                "type": "register",
                "capabilities": [JobType.PROCESSING.value]
            })
            websocket.receive_json()  # Registration ack

            # Send job failure
            websocket.send_json({
                "type": "job_status",
                "job_id": "job-456",
                "status": JobStatus.FAILED.value,
                "result": {
                    "error": "Processing error"
                }
            })

            # Connection should stay open

    def test_websocket_worker_ready(self) -> None:
        """Test worker ready signal via WebSocket"""
        client = TestClient(app)

        with client.websocket_connect(
                "/workers/test-worker-ready") as websocket:
            # Register
            websocket.send_json({
                "type": "register",
                "capabilities": [JobType.VALIDATION.value]
            })
            websocket.receive_json()  # Registration ack

            # Send ready signal
            websocket.send_json({"type": "ready"})

            # Worker should be marked as idle (no response expected)


@pytest.mark.integration
@pytest.mark.slow
class TestWorkerWebSocketReconnection:
    """Test worker WebSocket reconnection scenarios"""

    def test_disconnect_and_reconnect(self) -> None:
        """Test worker disconnection and reconnection"""
        client = TestClient(app)
        worker_id = "test-worker-reconnect"

        # First connection
        with client.websocket_connect(f"/workers/{worker_id}") as websocket:
            websocket.send_json({
                "type":
                "register",
                "capabilities":
                [JobType.VALIDATION.value, JobType.PROCESSING.value]
            })
            data = websocket.receive_json()
            assert data["type"] == "registration_ack"

        # Connection closed, reconnect
        with client.websocket_connect(f"/workers/{worker_id}") as websocket:
            websocket.send_json({
                "type":
                "register",
                "capabilities":
                [JobType.VALIDATION.value, JobType.PROCESSING.value]
            })
            data = websocket.receive_json()
            assert data["type"] == "registration_ack"
            assert data["worker_id"] == worker_id
