"""Integration tests for Job API endpoints"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, UTC
from typing import Any

from coordinator.main import app
from shared.enums import JobStatus, JobType, WorkflowStatus


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.mark.integration
class TestJobEndpoints:
    """Test job API endpoints"""

    def test_list_all_jobs(self, client: TestClient,
                           workflow_with_jobs) -> None:
        """Test listing all jobs across workflows"""
        workflow = workflow_with_jobs(client)
        response = client.get("/jobs")

        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= 3
        job_ids = [job["id"] for job in jobs]
        assert "job-1" in job_ids
        assert "job-2" in job_ids
        assert "job-3" in job_ids

    def test_list_jobs_filtered_by_workflow(self, client: TestClient,
                                            workflow_with_jobs) -> None:
        """Test listing jobs filtered by workflow ID"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        response = client.get(f"/jobs?workflow_id={workflow_id}")

        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 3
        assert all(job["id"] in ["job-1", "job-2", "job-3"] for job in jobs)

    def test_list_jobs_for_nonexistent_workflow(self,
                                                client: TestClient) -> None:
        """Test listing jobs for workflow that doesn't exist"""
        response = client.get("/jobs?workflow_id=nonexistent")

        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 0

    def test_get_job(self, client: TestClient, workflow_with_jobs) -> None:
        """Test getting a specific job"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        response = client.get(f"/jobs/{workflow_id}/job-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-1"
        assert data["type"] == JobType.VALIDATION.value
        assert data["status"] == JobStatus.PENDING

    def test_get_job_with_dependencies(self, client: TestClient,
                                       workflow_with_jobs) -> None:
        """Test getting job with on_success dependency"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        response = client.get(f"/jobs/{workflow_id}/job-2")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-2"
        assert data["on_success"] == "job-3"

    def test_get_nonexistent_job(self, client: TestClient,
                                 workflow_with_jobs) -> None:
        """Test getting job that doesn't exist"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        response = client.get(f"/jobs/{workflow_id}/nonexistent-job")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_job_from_nonexistent_workflow(self,
                                               client: TestClient) -> None:
        """Test getting job from workflow that doesn't exist"""
        response = client.get("/jobs/nonexistent-workflow/job-1")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_job_status(
            self, client: TestClient, workflow_with_jobs,
            sample_job_parameters: dict[JobType, dict[str, Any]]) -> None:
        """Test updating a job's status"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]

        # Get current job
        get_response = client.get(f"/jobs/{workflow_id}/job-1")
        job_data = get_response.json()

        # Update status
        job_data["status"] = JobStatus.RUNNING.value
        job_data["worker_id"] = "worker-123"

        response = client.patch(f"/jobs/{workflow_id}/job-1", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.RUNNING.value
        assert data["worker_id"] == "worker-123"

    def test_update_job_with_result(self, client: TestClient,
                                    workflow_with_jobs) -> None:
        """Test updating job with execution result"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]

        # Get current job
        get_response = client.get(f"/jobs/{workflow_id}/job-1")
        job_data = get_response.json()

        # Update with result
        job_data["status"] = JobStatus.COMPLETED.value
        job_data["result"] = {"validated": True, "record_count": 150}

        response = client.patch(f"/jobs/{workflow_id}/job-1", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.COMPLETED.value
        assert data["result"]["validated"] is True
        assert data["result"]["record_count"] == 150

    def test_update_job_with_error(self, client: TestClient,
                                   workflow_with_jobs) -> None:
        """Test updating job with error information"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]

        # Get current job
        get_response = client.get(f"/jobs/{workflow_id}/job-2")
        job_data = get_response.json()

        # Update with error
        job_data["status"] = JobStatus.FAILED.value
        job_data["error"] = "Connection timeout after 30 seconds"
        job_data["retry_count"] = 1

        response = client.patch(f"/jobs/{workflow_id}/job-2", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.FAILED.value
        assert data["error"] == "Connection timeout after 30 seconds"
        assert data["retry_count"] == 1

    def test_update_nonexistent_job(
            self, client: TestClient, workflow_with_jobs,
            sample_job_parameters: dict[JobType, dict[str, Any]]) -> None:
        """Test updating job that doesn't exist"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        job_data = {
            "id": "nonexistent-job",
            "type": JobType.VALIDATION.value,
            "parameters": sample_job_parameters[JobType.VALIDATION],
            "status": JobStatus.RUNNING.value,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }

        response = client.patch(f"/jobs/{workflow_id}/nonexistent-job",
                                json=job_data)

        assert response.status_code == 404

    def test_update_job_in_nonexistent_workflow(
            self, client: TestClient,
            sample_job_parameters: dict[JobType, dict[str, Any]]) -> None:
        """Test updating job in workflow that doesn't exist"""
        job_data = {
            "id": "job-1",
            "type": JobType.VALIDATION.value,
            "parameters": sample_job_parameters[JobType.VALIDATION],
            "status": JobStatus.RUNNING.value,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }

        response = client.patch("/jobs/nonexistent-workflow/job-1",
                                json=job_data)

        assert response.status_code == 404


@pytest.mark.integration
class TestJobLifecycle:
    """Test complete job lifecycle scenarios"""

    def test_job_progression_through_states(self, client: TestClient,
                                            workflow_with_jobs) -> None:
        """Test job progressing through different states"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        job_id = "job-1"

        # 1. Job starts as PENDING
        response = client.get(f"/jobs/{workflow_id}/{job_id}")
        assert response.json()["status"] == JobStatus.PENDING

        # 2. Assign to worker and mark as RUNNING
        job_data = response.json()
        job_data["status"] = JobStatus.RUNNING.value
        job_data["worker_id"] = "worker-1"
        response = client.patch(f"/jobs/{workflow_id}/{job_id}", json=job_data)
        assert response.json()["status"] == JobStatus.RUNNING.value

        # 3. Complete with result
        job_data = response.json()
        job_data["status"] = JobStatus.COMPLETED.value
        job_data["result"] = {"success": True}
        response = client.patch(f"/jobs/{workflow_id}/{job_id}", json=job_data)
        assert response.json()["status"] == JobStatus.COMPLETED.value

    def test_job_retry_scenario(self, client: TestClient,
                                workflow_with_jobs) -> None:
        """Test job retry behavior"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]
        job_id = "job-2"

        # Get job
        response = client.get(f"/jobs/{workflow_id}/{job_id}")
        job_data = response.json()
        initial_retry_count = job_data["retry_count"]

        # Mark as failed with retry
        job_data["status"] = JobStatus.FAILED.value
        job_data["error"] = "Temporary network issue"
        job_data["retry_count"] = initial_retry_count + 1

        response = client.patch(f"/jobs/{workflow_id}/{job_id}", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data["retry_count"] == initial_retry_count + 1
        assert data["status"] == JobStatus.FAILED.value

    def test_multiple_jobs_in_workflow(self, client: TestClient,
                                       workflow_with_jobs) -> None:
        """Test managing multiple jobs within a workflow"""
        workflow = workflow_with_jobs(client)
        workflow_id = workflow["id"]

        # Get all jobs for the workflow
        response = client.get(f"/jobs?workflow_id={workflow_id}")
        jobs = response.json()
        assert len(jobs) == 3

        # Update multiple jobs
        for i, job in enumerate(jobs):
            job["status"] = JobStatus.RUNNING.value
            job["worker_id"] = f"worker-{i+1}"
            update_response = client.patch(f"/jobs/{workflow_id}/{job['id']}",
                                           json=job)
            assert update_response.status_code == 200

        # Verify all updates
        response = client.get(f"/jobs?workflow_id={workflow_id}")
        updated_jobs = response.json()
        assert all(job["status"] == JobStatus.RUNNING.value
                   for job in updated_jobs)
