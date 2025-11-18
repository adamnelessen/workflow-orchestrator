from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Tuple
from datetime import UTC, datetime

from shared.models import Job, Workflow
from coordinator.core.state_manager import StateManager, state_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _get_workflow_and_job(workflow_id: str, job_id: str,
                          state: StateManager) -> Tuple[Workflow, Job, int]:
    """Helper to get workflow and job with validation
    
    Returns:
        Tuple of (workflow, job, job_index)
        
    Raises:
        HTTPException: If workflow or job not found
    """
    workflow = await state.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    job_index = next(
        (i for i, j in enumerate(workflow.jobs) if j.id == job_id), None)
    if job_index is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job = workflow.jobs[job_index]
    return workflow, job, job_index


@router.get("", response_model=List[Job])
async def list_jobs(workflow_id: Optional[str] = None,
                    state: StateManager = Depends(state_manager)):
    """List all jobs, optionally filtered by workflow"""
    jobs = []
    for workflow in state.list_workflows():
        if workflow_id is None or workflow.id == workflow_id:
            jobs.extend(workflow.jobs)
    return jobs


@router.get("/{workflow_id}/{job_id}", response_model=Job)
async def get_job(workflow_id: str,
                  job_id: str,
                  state: StateManager = Depends(state_manager)):
    """Get a specific job from a workflow"""
    _, job, _ = await _get_workflow_and_job(workflow_id, job_id, state)
    return job


@router.patch("/{workflow_id}/{job_id}", response_model=Job)
async def update_job(workflow_id: str,
                     job_id: str,
                     job_update: Job,
                     state: StateManager = Depends(state_manager)):
    """Update a job's details"""
    workflow, _, job_index = await _get_workflow_and_job(workflow_id, job_id, state)

    job_update.updated_at = datetime.now(UTC)
    workflow.jobs[job_index] = job_update
    workflow.updated_at = datetime.now(UTC)
    return job_update
