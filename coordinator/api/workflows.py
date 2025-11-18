from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from datetime import UTC, datetime

from shared.models import Workflow
from coordinator.utils.workflow_parser import parse_yaml_workflow, WorkflowDefinitionError
from coordinator.core.state_manager import StateManager, state_manager
from coordinator.core.dependencies import get_workflow_engine
from coordinator.core.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def _get_workflow_or_404(workflow_id: str, state: StateManager) -> Workflow:
    """Get a workflow by ID or raise 404 if not found"""
    workflow = await state.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


async def _ensure_workflow_not_exists(workflow_id: str, state: StateManager) -> None:
    """Raise 400 if workflow already exists"""
    if await state.get_workflow(workflow_id) is not None:
        raise HTTPException(status_code=400, detail="Workflow already exists")


async def _add_workflow_to_state(workflow: Workflow,
                           state: StateManager) -> Workflow:
    """Add workflow to state with timestamps set"""
    workflow.created_at = datetime.now(UTC)
    workflow.updated_at = datetime.now(UTC)
    await state.add_workflow(workflow)
    return workflow


@router.post("", response_model=Workflow)
async def create_workflow(workflow: Workflow,
                          state: StateManager = Depends(state_manager)):
    """Create a new workflow"""
    await _ensure_workflow_not_exists(workflow.id, state)
    return await _add_workflow_to_state(workflow, state)


@router.post("/from-yaml", response_model=Workflow)
async def create_workflow_from_yaml(
        yaml_content: str = Body(..., media_type="text/plain"),
        state: StateManager = Depends(state_manager)):
    """Create a new workflow from YAML definition
    
    Example YAML:
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
            always_run: true
    ```
    """
    try:
        workflow = parse_yaml_workflow(yaml_content)
    except WorkflowDefinitionError as e:
        raise HTTPException(status_code=400,
                            detail=f"Invalid workflow definition: {e}")

    await _ensure_workflow_not_exists(workflow.id, state)

    # Add workflow and all its jobs to state
    await _add_workflow_to_state(workflow, state)
    for job in workflow.jobs:
        await state.add_job(job)

    return workflow


@router.post("/{workflow_id}/start")
async def start_workflow(
    workflow_id: str,
    state: StateManager = Depends(state_manager),
    engine: WorkflowEngine = Depends(get_workflow_engine)):
    """Start a workflow execution"""
    await _get_workflow_or_404(workflow_id, state)

    success = await engine.start_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start workflow")

    return {"message": "Workflow started", "workflow_id": workflow_id}


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    state: StateManager = Depends(state_manager),
    engine: WorkflowEngine = Depends(get_workflow_engine)):
    """Cancel a running workflow"""
    await _get_workflow_or_404(workflow_id, state)

    success = await engine.cancel_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400,
                            detail="Failed to cancel workflow")

    return {"message": "Workflow cancelled", "workflow_id": workflow_id}


@router.get("", response_model=List[Workflow])
async def list_workflows(state: StateManager = Depends(state_manager)):
    """List all workflows"""
    return state.list_workflows()


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str,
                       state: StateManager = Depends(state_manager)):
    """Get a specific workflow"""
    return await _get_workflow_or_404(workflow_id, state)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str,
                          state: StateManager = Depends(state_manager)):
    """Delete a workflow"""
    await _get_workflow_or_404(workflow_id, state)
    await state.remove_workflow(workflow_id)
    return {"message": "Workflow deleted"}
