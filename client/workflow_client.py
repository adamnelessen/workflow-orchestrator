"""Sample client to interact with the Northwood Workflow Orchestration System."""
import requests
import time
from typing import List
from shared.models import Worker


class WorkflowClient:
    """Client for interacting with the workflow coordinator."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the client."""
        self.base_url = base_url

    # TODO: Implement & test these methods as needed
    # def submit_workflow(self, workflow: dict) -> str:
    #     """Submit a workflow to the coordinator."""
    #     response = requests.post(f"{self.base_url}/workflows", json=workflow)
    #     response.raise_for_status()
    #     return response.json()["workflow_id"]

    # def get_workflow_status(self, workflow_id: str) -> dict:
    #     """Get the status of a workflow."""
    #     response = requests.get(f"{self.base_url}/workflows/{workflow_id}")
    #     response.raise_for_status()
    #     return response.json()

    # def get_workflow_jobs(self, workflow_id: str) -> List[dict]:
    #     """Get all jobs in a workflow."""
    #     response = requests.get(
    #         f"{self.base_url}/workflows/{workflow_id}/jobs")
    #     response.raise_for_status()
    #     return response.json()

    # def get_job_status(self, job_id: str) -> dict:
    #     """Get the status of a job."""
    #     response = requests.get(f"{self.base_url}/jobs/{job_id}")
    #     response.raise_for_status()
    #     return response.json()

    def get_workers(self) -> List[Worker]:
        """Get list of connected workers."""
        response = requests.get(f"{self.base_url}/workers")
        response.raise_for_status()
        return [Worker.model_validate(worker) for worker in response.json()]

    # def wait_for_workflow(self, workflow_id: str, timeout: int = 60) -> dict:
    #     """Wait for a workflow to complete."""
    #     start_time = time.time()

    #     while time.time() - start_time < timeout:
    #         status = self.get_workflow_status(workflow_id)

    #         if status["status"] in [
    #                 "completed", "failed", "partially_completed"
    #         ]:
    #             return status

    #         time.sleep(2)

    #     raise TimeoutError(
    #         f"Workflow {workflow_id} did not complete within {timeout} seconds"
    #     )
