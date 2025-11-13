from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from shared.schemas import Workflow
from coordinator.core.storage import workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=Workflow)
async def create_workflow(workflow: Workflow):
    """Create a new workflow"""
    if workflow.id in workflows:
        raise HTTPException(status_code=400, detail="Workflow already exists")

    workflow.created_at = datetime.now()
    workflow.updated_at = datetime.now()
    workflows[workflow.id] = workflow
    return workflow


@router.get("", response_model=List[Workflow])
async def list_workflows():
    """List all workflows"""
    return list(workflows.values())


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """Get a specific workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows[workflow_id]


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    del workflows[workflow_id]
    return {"message": "Workflow deleted"}
