"""Sample client to interact with the Workflow Orchestration System."""
import requests
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from shared.models import Worker, Workflow


class WorkflowClient:
    """Client for interacting with the workflow coordinator."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the client."""
        self.base_url = base_url

    def get_workers(self) -> List[Worker]:
        """Get list of connected workers."""
        response = requests.get(f"{self.base_url}/workers")
        response.raise_for_status()
        return [Worker.model_validate(worker) for worker in response.json()]

    def submit_workflow_from_yaml(self, yaml_path: str) -> Workflow:
        """Submit a workflow from a YAML file.
        
        Args:
            yaml_path: Path to the YAML workflow definition file
            
        Returns:
            Workflow: The created workflow
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            requests.HTTPError: If the API request fails
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        yaml_content = path.read_text()

        response = requests.post(f"{self.base_url}/workflows/from-yaml",
                                 data=yaml_content,
                                 headers={"Content-Type": "text/plain"})
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def start_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Start a workflow execution.
        
        Args:
            workflow_id: ID of the workflow to start
            
        Returns:
            Dict containing the response message and workflow_id
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        response = requests.post(
            f"{self.base_url}/workflows/{workflow_id}/start")
        response.raise_for_status()
        return response.json()

    def submit_and_start_workflow(self, yaml_path: str) -> Workflow:
        """Submit a workflow from a YAML file and immediately start it.
        
        Args:
            yaml_path: Path to the YAML workflow definition file
            
        Returns:
            Workflow: The created and started workflow
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            requests.HTTPError: If the API request fails
        """
        workflow = self.submit_workflow_from_yaml(yaml_path)
        self.start_workflow(workflow.id)
        return workflow

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get a workflow by ID.
        
        Args:
            workflow_id: ID of the workflow to retrieve
            
        Returns:
            Workflow: The workflow
            
        Raises:
            requests.HTTPError: If the API request fails (e.g., 404 if not found)
        """
        response = requests.get(f"{self.base_url}/workflows/{workflow_id}")
        response.raise_for_status()
        return Workflow.model_validate(response.json())

    def list_workflows(self) -> List[Workflow]:
        """Get list of all workflows.
        
        Returns:
            List of all workflows
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        response = requests.get(f"{self.base_url}/workflows")
        response.raise_for_status()
        return [Workflow.model_validate(wf) for wf in response.json()]

    def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Cancel a running workflow.
        
        Args:
            workflow_id: ID of the workflow to cancel
            
        Returns:
            Dict containing the response message and workflow_id
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        response = requests.post(
            f"{self.base_url}/workflows/{workflow_id}/cancel")
        response.raise_for_status()
        return response.json()

    def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Delete a workflow.
        
        Args:
            workflow_id: ID of the workflow to delete
            
        Returns:
            Dict containing the response message and workflow_id
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        response = requests.delete(f"{self.base_url}/workflows/{workflow_id}")
        response.raise_for_status()
        return response.json()
