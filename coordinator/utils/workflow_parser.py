"""Workflow definition parser for YAML format"""
from typing import Dict, Any, List
from datetime import datetime, UTC
import yaml
import uuid

from shared.models import Workflow, Job
from shared.enums import JobType, JobStatus, WorkflowStatus


class WorkflowDefinitionError(Exception):
    """Raised when workflow definition is invalid"""
    pass


def parse_yaml_workflow(yaml_content: str) -> Workflow:
    """Parse a YAML workflow definition into a Workflow model.
    
    Expected YAML format:
    ```yaml
    workflow:
      name: "data-processing-pipeline"
      jobs:
        - id: "validate-input"
            type: "validation"
            parameters:
                schema: "user-data"
            on_success: "process-data"
            on_failure: "send-error-notification"
        - id: "process-data"
            type: "processing"
            parameters:
                operation: "transform"
            on_success: "save-results"
            always_run: true
    ```
    
    Args:
        yaml_content: YAML string containing workflow definition
        
    Returns:
        Workflow: Parsed and validated workflow
        
    Raises:
        WorkflowDefinitionError: If YAML is invalid or missing required fields
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise WorkflowDefinitionError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise WorkflowDefinitionError("YAML must contain a dictionary")

    if "workflow" not in data:
        raise WorkflowDefinitionError("YAML must contain 'workflow' key")

    workflow_def = data["workflow"]

    # Validate required fields
    if "name" not in workflow_def:
        raise WorkflowDefinitionError("Workflow must have a 'name'")

    if "jobs" not in workflow_def or not isinstance(workflow_def["jobs"],
                                                    list):
        raise WorkflowDefinitionError("Workflow must have a 'jobs' list")

    if len(workflow_def["jobs"]) == 0:
        raise WorkflowDefinitionError("Workflow must have at least one job")

    # Parse jobs
    jobs = []
    job_ids = set()

    for idx, job_def in enumerate(workflow_def["jobs"]):
        try:
            job = _parse_job(job_def, idx)

            # Check for duplicate job IDs
            if job.id in job_ids:
                raise WorkflowDefinitionError(f"Duplicate job ID: {job.id}")
            job_ids.add(job.id)

            jobs.append(job)
        except (KeyError, ValueError, TypeError) as e:
            raise WorkflowDefinitionError(
                f"Error parsing job at index {idx}: {e}")

    # Validate job references (on_success, on_failure)
    _validate_job_references(jobs, job_ids)

    # Create workflow
    workflow_id = workflow_def.get("id", str(uuid.uuid4()))
    now = datetime.now(UTC)

    workflow = Workflow(id=workflow_id,
                        name=workflow_def["name"],
                        status=WorkflowStatus.PENDING,
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    return workflow


def _parse_job(job_def: Dict[str, Any], index: int) -> Job:
    """Parse a single job definition.
    
    Args:
        job_def: Dictionary containing job definition
        index: Index of job in the workflow (for error reporting)
        
    Returns:
        Job: Parsed job
        
    Raises:
        WorkflowDefinitionError: If job definition is invalid
    """
    if not isinstance(job_def, dict):
        raise WorkflowDefinitionError(
            f"Job at index {index} must be a dictionary")

    # Validate required fields
    if "id" not in job_def:
        raise WorkflowDefinitionError(
            f"Job at index {index} must have an 'id'")

    if "type" not in job_def:
        raise WorkflowDefinitionError(
            f"Job '{job_def['id']}' must have a 'type'")

    # Validate job type
    try:
        job_type = JobType(job_def["type"])
    except ValueError:
        valid_types = [t.value for t in JobType]
        raise WorkflowDefinitionError(
            f"Job '{job_def['id']}' has invalid type '{job_def['type']}'. "
            f"Valid types: {valid_types}")

    # Get parameters (default to empty dict)
    parameters = job_def.get("parameters", {})
    if not isinstance(parameters, dict):
        raise WorkflowDefinitionError(
            f"Job '{job_def['id']}' parameters must be a dictionary")

    # Get optional fields
    on_success = job_def.get("on_success")
    on_failure = job_def.get("on_failure")
    always_run = job_def.get("always_run", False)
    max_retries = job_def.get("max_retries", 3)

    # Normalize on_success and on_failure to always be lists (or None)
    if on_success is not None:
        if isinstance(on_success, str):
            on_success = [on_success]
        elif isinstance(on_success, list):
            if not all(isinstance(j, str) for j in on_success):
                raise WorkflowDefinitionError(
                    f"Job '{job_def['id']}' on_success list must contain only strings"
                )
        else:
            raise WorkflowDefinitionError(
                f"Job '{job_def['id']}' on_success must be a string or list of strings"
            )

    if on_failure is not None:
        if isinstance(on_failure, str):
            on_failure = [on_failure]
        elif isinstance(on_failure, list):
            if not all(isinstance(j, str) for j in on_failure):
                raise WorkflowDefinitionError(
                    f"Job '{job_def['id']}' on_failure list must contain only strings"
                )
        else:
            raise WorkflowDefinitionError(
                f"Job '{job_def['id']}' on_failure must be a string or list of strings"
            )

    if not isinstance(always_run, bool):
        raise WorkflowDefinitionError(
            f"Job '{job_def['id']}' always_run must be a boolean")

    if not isinstance(max_retries, int) or max_retries < 0:
        raise WorkflowDefinitionError(
            f"Job '{job_def['id']}' max_retries must be a non-negative integer"
        )

    now = datetime.now(UTC)

    return Job(id=job_def["id"],
               type=job_type,
               parameters=parameters,
               status=JobStatus.PENDING,
               on_success=on_success,
               on_failure=on_failure,
               always_run=always_run,
               max_retries=max_retries,
               created_at=now,
               updated_at=now)


def _validate_job_references(jobs: List[Job], job_ids: set):
    """Validate that on_success and on_failure references point to valid jobs.
    
    Args:
        jobs: List of parsed jobs
        job_ids: Set of all job IDs in the workflow
        
    Raises:
        WorkflowDefinitionError: If a job references a non-existent job
    """
    for job in jobs:
        # Validate on_success references (always a list)
        if job.on_success:
            for ref in job.on_success:
                if ref not in job_ids:
                    raise WorkflowDefinitionError(
                        f"Job '{job.id}' references non-existent job in on_success: '{ref}'"
                    )

        # Validate on_failure references (always a list)
        if job.on_failure:
            for ref in job.on_failure:
                if ref not in job_ids:
                    raise WorkflowDefinitionError(
                        f"Job '{job.id}' references non-existent job in on_failure: '{ref}'"
                    )


def workflow_to_yaml(workflow: Workflow) -> str:
    """Convert a Workflow model to YAML format.
    
    Args:
        workflow: Workflow to convert
        
    Returns:
        str: YAML representation of the workflow
    """
    workflow_dict = {
        "workflow": {
            "id": workflow.id,
            "name": workflow.name,
            "jobs": []
        }
    }

    for job in workflow.jobs:
        job_dict = {
            "id": job.id,
            "type": job.type.value,
            "parameters": job.parameters
        }

        if job.on_success:
            job_dict["on_success"] = job.on_success

        if job.on_failure:
            job_dict["on_failure"] = job.on_failure

        if job.always_run:
            job_dict["always_run"] = job.always_run

        if job.max_retries != 3:
            job_dict["max_retries"] = job.max_retries

        workflow_dict["workflow"]["jobs"].append(job_dict)

    return yaml.dump(workflow_dict, sort_keys=False, default_flow_style=False)
