"""Integration tests for Health check endpoints"""
import pytest
from fastapi.testclient import TestClient

from coordinator.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root health check"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "coordinator"
        assert data["status"] == "running"
        assert "timestamp" in data

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test detailed health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "workflows" in data
        assert "workers" in data
        assert "active_workers" in data
