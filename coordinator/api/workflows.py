from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import UTC, datetime

from shared.models import Workflow
from coordinator.core.state_manager import StateManager, state_manager

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=Workflow)
async def create_workflow(workflow: Workflow,
                          state: StateManager = Depends(state_manager)):
    """Create a new workflow"""
    if state.get_workflow(workflow.id) is not None:
        raise HTTPException(status_code=400, detail="Workflow already exists")

    workflow.created_at = datetime.now(UTC)
    workflow.updated_at = datetime.now(UTC)
    state.add_workflow(workflow)
    return workflow


@router.get("", response_model=List[Workflow])
async def list_workflows(state: StateManager = Depends(state_manager)):
    """List all workflows"""
    return state.list_workflows()


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str,
                       state: StateManager = Depends(state_manager)):
    """Get a specific workflow"""
    workflow = state.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str,
                          state: StateManager = Depends(state_manager)):
    """Delete a workflow"""
    workflow = state.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    state.remove_workflow(workflow_id)
    return {"message": "Workflow deleted"}
