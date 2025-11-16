"""Integration tests for Workflow API endpoints"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, UTC
from typing import Any

from coordinator.main import app
from shared.enums import WorkflowStatus, JobType


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.mark.integration
class TestWorkflowEndpoints:
    """Test workflow API endpoints"""

    def test_create_workflow(self, client: TestClient,
                             sample_workflow_config: dict[str, Any]) -> None:
        """Test creating a new workflow"""
        response = client.post("/workflows",
                               json={
                                   "id": "wf-test-1",
                                   "name": sample_workflow_config["name"],
                                   "jobs": sample_workflow_config["jobs"],
                                   "created_at": datetime.now(UTC).isoformat(),
                                   "updated_at": datetime.now(UTC).isoformat()
                               })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf-test-1"
        assert data["name"] == sample_workflow_config["name"]
        assert data["status"] == WorkflowStatus.PENDING

    def test_create_duplicate_workflow(self, client: TestClient) -> None:
        """Test creating workflow with duplicate ID"""
        workflow_data = {
            "id": "wf-dup",
            "name": "Duplicate Test",
            "jobs": [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }

        # Create first time
        response1 = client.post("/workflows", json=workflow_data)
        assert response1.status_code == 200

        # Try to create again
        response2 = client.post("/workflows", json=workflow_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    def test_list_workflows(self, client: TestClient) -> None:
        """Test listing all workflows"""
        # Create some workflows
        for i in range(3):
            client.post("/workflows",
                        json={
                            "id": f"wf-list-{i}",
                            "name": f"Workflow {i}",
                            "jobs": [],
                            "created_at": datetime.now(UTC).isoformat(),
                            "updated_at": datetime.now(UTC).isoformat()
                        })

        response = client.get("/workflows")

        assert response.status_code == 200
        workflows = response.json()
        assert len(workflows) >= 3

    def test_get_workflow(self, client: TestClient) -> None:
        """Test getting a specific workflow"""
        # Create workflow
        workflow_id = "wf-get-test"
        client.post("/workflows",
                    json={
                        "id": workflow_id,
                        "name": "Get Test",
                        "jobs": [],
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat()
                    })

        # Get workflow
        response = client.get(f"/workflows/{workflow_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workflow_id

    def test_get_nonexistent_workflow(self, client: TestClient) -> None:
        """Test getting workflow that doesn't exist"""
        response = client.get("/workflows/nonexistent")

        assert response.status_code == 404

    def test_delete_workflow(self, client: TestClient) -> None:
        """Test deleting a workflow"""
        # Create workflow
        workflow_id = "wf-delete-test"
        client.post("/workflows",
                    json={
                        "id": workflow_id,
                        "name": "Delete Test",
                        "jobs": [],
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat()
                    })

        # Delete workflow
        response = client.delete(f"/workflows/{workflow_id}")

        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/workflows/{workflow_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_workflow(self, client: TestClient) -> None:
        """Test deleting workflow that doesn't exist"""
        response = client.delete("/workflows/nonexistent")

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkflowWithJobs:
    """Test workflows with job configurations"""

    def test_create_workflow_with_jobs(
            self, client: TestClient,
            sample_job_parameters: dict[JobType, dict[str, Any]]) -> None:
        """Test creating workflow with multiple jobs"""
        workflow_data = {
            "id":
            "wf-jobs",
            "name":
            "Pipeline with Jobs",
            "jobs": [{
                "id": "job-1",
                "type": JobType.VALIDATION.value,
                "parameters": sample_job_parameters[JobType.VALIDATION],
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }, {
                "id": "job-2",
                "type": JobType.PROCESSING.value,
                "parameters": sample_job_parameters[JobType.PROCESSING],
                "on_success": "job-3",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat()
            }],
            "created_at":
            datetime.now(UTC).isoformat(),
            "updated_at":
            datetime.now(UTC).isoformat()
        }

        response = client.post("/workflows", json=workflow_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["jobs"][1]["on_success"] == "job-3"
