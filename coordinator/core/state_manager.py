"""In-memory state management for workflows and workers"""
from typing import Dict, Optional
from shared.models import Workflow, Worker, Job
import asyncio
from fastapi import WebSocket


class StateManager:
    """Centralized state for workflows, workers, and job state"""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.workers: Dict[str, Worker] = {}
        self.jobs: Dict[str, Job] = {}
        self.job_assignments: Dict[str, str] = {}  # job_id -> worker_id
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_jobs: asyncio.Queue = asyncio.Queue()

    # Workflow methods
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.workflows.get(workflow_id)

    def add_workflow(self, workflow: Workflow) -> None:
        self.workflows[workflow.id] = workflow

    def remove_workflow(self, workflow_id: str) -> None:
        self.workflows.pop(workflow_id, None)

    def list_workflows(self) -> list[Workflow]:
        return list(self.workflows.values())

    # Worker methods
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        return self.workers.get(worker_id)

    def add_worker(self, worker: Worker) -> None:
        self.workers[worker.id] = worker

    def remove_worker(self, worker_id: str) -> None:
        self.workers.pop(worker_id, None)

    def list_workers(self) -> list[Worker]:
        return list(self.workers.values())

    # Job methods
    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def add_job(self, job: Job) -> None:
        self.jobs[job.id] = job

    def remove_job(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

    def list_jobs(self) -> list[Job]:
        return list(self.jobs.values())

    # Job assignment methods
    def assign_job(self, job_id: str, worker_id: str) -> None:
        self.job_assignments[job_id] = worker_id

    def get_job_worker(self, job_id: str) -> Optional[str]:
        return self.job_assignments.get(job_id)

    def unassign_job(self, job_id: str) -> None:
        self.job_assignments.pop(job_id, None)

    def list_job_assignments(self) -> Dict[str, str]:
        """Return all job assignments as a dictionary"""
        return dict(self.job_assignments)

    def get_worker_jobs(self, worker_id: str) -> list[str]:
        """Get all job IDs assigned to a specific worker"""
        return [
            job_id for job_id, wid in self.job_assignments.items()
            if wid == worker_id
        ]

    def count_worker_jobs(self, worker_id: str) -> int:
        """Count the number of jobs assigned to a specific worker"""
        return sum(1 for wid in self.job_assignments.values()
                   if wid == worker_id)

    def is_job_assigned(self, job_id: str) -> bool:
        """Check if a job is currently assigned to any worker"""
        return job_id in self.job_assignments

    def clear_job_assignments(self) -> None:
        """Clear all job assignments"""
        self.job_assignments.clear()


# Global state instance
_state: Optional[StateManager] = None


def state_manager() -> StateManager:
    """Dependency injection function for FastAPI"""
    global _state
    if _state is None:
        _state = StateManager()
    return _state
