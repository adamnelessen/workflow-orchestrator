"""Hybrid state management with PostgreSQL persistence and Redis caching"""
from typing import Dict, Optional
from shared.models import Workflow, Worker, Job
import asyncio
from fastapi import WebSocket
from coordinator.db.postgres import PostgresDB
from coordinator.db.redis import RedisCache


class StateManager:
    """Centralized state with optional PostgreSQL + Redis backends"""

    def __init__(self,
                 postgres: Optional[PostgresDB] = None,
                 redis: Optional[RedisCache] = None):
        # In-memory state (fallback and for WebSocket connections)
        self.workflows: Dict[str, Workflow] = {}
        self.workers: Dict[str, Worker] = {}
        self.jobs: Dict[str, Job] = {}
        self.job_assignments: Dict[str, str] = {}  # job_id -> worker_id
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_jobs: asyncio.Queue = asyncio.Queue()

        # Database backends (optional)
        self.postgres = postgres
        self.redis = redis
        self._use_db = postgres is not None

    # Workflow methods
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow from cache or DB"""
        # Try in-memory first
        if workflow_id in self.workflows:
            return self.workflows[workflow_id]

        # Try Redis cache
        if self.redis:
            cached = await self.redis.get_cached_workflow(workflow_id)
            if cached:
                workflow = Workflow(**cached)
                self.workflows[workflow_id] = workflow
                return workflow

        # Try PostgreSQL
        if self.postgres:
            model = await self.postgres.get_workflow(workflow_id)
            if model:
                # Reconstruct Workflow with jobs
                job_models = await self.postgres.list_jobs_by_workflow(
                    workflow_id)
                jobs = [
                    Job(
                        id=j.id,
                        type=j.type,
                        parameters=j.parameters,
                        status=j.status,
                        worker_id=j.worker_id,
                        result=j.result,
                        error=j.error,
                        retry_count=j.retry_count,
                        max_retries=j.max_retries,
                        on_success=j.on_success,
                        on_failure=j.on_failure,
                        always_run=j.always_run,
                        created_at=j.created_at,
                        updated_at=j.updated_at,
                    ) for j in job_models
                ]
                workflow = Workflow(
                    id=model.id,
                    name=model.name,
                    status=model.status,
                    jobs=jobs,
                    current_jobs=model.current_jobs,
                    completed_jobs=model.completed_jobs,
                    failed_jobs=model.failed_jobs,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                # Cache it
                self.workflows[workflow_id] = workflow
                for job in jobs:
                    self.jobs[job.id] = job
                return workflow

        return None

    async def add_workflow(self, workflow: Workflow) -> None:
        """Add workflow to memory and persist"""
        self.workflows[workflow.id] = workflow

        # Add jobs to memory
        for job in workflow.jobs:
            self.jobs[job.id] = job

        # Persist to DB
        if self.postgres:
            await self.postgres.save_workflow(workflow)
            for job in workflow.jobs:
                await self.postgres.save_job(job, workflow.id)

        # Cache in Redis
        if self.redis:
            await self.redis.cache_workflow(workflow)
            for job in workflow.jobs:
                await self.redis.cache_job(job)

    async def remove_workflow(self, workflow_id: str) -> None:
        """Remove workflow from memory and DB"""
        self.workflows.pop(workflow_id, None)

        if self.postgres:
            await self.postgres.delete_workflow(workflow_id)

        if self.redis:
            await self.redis.invalidate_workflow(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """List workflows from memory"""
        return list(self.workflows.values())

    # Worker methods
    async def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get worker from cache or DB"""
        if worker_id in self.workers:
            return self.workers[worker_id]

        if self.postgres:
            model = await self.postgres.get_worker(worker_id)
            if model:
                from shared.enums import JobType
                worker = Worker(
                    id=model.id,
                    status=model.status,
                    capabilities=[JobType(cap) for cap in model.capabilities],
                    current_job_id=model.current_job_id,
                    last_heartbeat=model.last_heartbeat,
                    registered_at=model.registered_at,
                )
                self.workers[worker_id] = worker
                return worker

        return None

    async def add_worker(self, worker: Worker) -> None:
        """Add worker to memory and persist"""
        self.workers[worker.id] = worker

        if self.postgres:
            await self.postgres.save_worker(worker)

        if self.redis:
            await self.redis.mark_worker_active(worker.id, ttl=30)

    async def remove_worker(self, worker_id: str) -> None:
        """Remove worker from memory and DB"""
        self.workers.pop(worker_id, None)

        if self.postgres:
            await self.postgres.delete_worker(worker_id)

        if self.redis:
            await self.redis.remove_worker(worker_id)

    def list_workers(self) -> list[Worker]:
        """List workers from memory"""
        return list(self.workers.values())

    # Job methods
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job from cache or DB"""
        if job_id in self.jobs:
            return self.jobs[job_id]

        if self.redis:
            cached = await self.redis.get_cached_job(job_id)
            if cached:
                job = Job(**cached)
                self.jobs[job_id] = job
                return job

        if self.postgres:
            model = await self.postgres.get_job(job_id)
            if model:
                job = Job(
                    id=model.id,
                    type=model.type,
                    parameters=model.parameters,
                    status=model.status,
                    worker_id=model.worker_id,
                    result=model.result,
                    error=model.error,
                    retry_count=model.retry_count,
                    max_retries=model.max_retries,
                    on_success=model.on_success,
                    on_failure=model.on_failure,
                    always_run=model.always_run,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                self.jobs[job_id] = job
                return job

        return None

    async def add_job(self, job: Job) -> None:
        """Add job to memory and persist"""
        self.jobs[job.id] = job

        # Find workflow for this job
        workflow_id = None
        for wf in self.workflows.values():
            if any(j.id == job.id for j in wf.jobs):
                workflow_id = wf.id
                break

        if self.postgres and workflow_id:
            await self.postgres.save_job(job, workflow_id)

        if self.redis:
            await self.redis.cache_job(job)

    async def remove_job(self, job_id: str) -> None:
        """Remove job from memory"""
        self.jobs.pop(job_id, None)

        if self.redis:
            await self.redis.invalidate_job(job_id)

    def list_jobs(self) -> list[Job]:
        """List jobs from memory"""
        return list(self.jobs.values())

    # Job assignment methods
    async def assign_job(self, job_id: str, worker_id: str) -> None:
        """Assign job to worker"""
        self.job_assignments[job_id] = worker_id

        if self.postgres:
            await self.postgres.save_assignment(job_id, worker_id)

    async def get_job_worker(self, job_id: str) -> Optional[str]:
        """Get worker assigned to job"""
        if job_id in self.job_assignments:
            return self.job_assignments[job_id]

        if self.postgres:
            return await self.postgres.get_assignment(job_id)

        return None

    async def unassign_job(self, job_id: str) -> None:
        """Unassign job from worker"""
        self.job_assignments.pop(job_id, None)

        if self.postgres:
            await self.postgres.delete_assignment(job_id)

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

    async def _rebuild_from_db(self) -> None:
        """Rebuild in-memory cache from PostgreSQL after restart"""
        if not self.postgres:
            return

        from shared.enums import JobType

        # Load all workflows with their jobs
        workflow_models = await self.postgres.list_workflows()
        for wf_model in workflow_models:
            # Get all jobs for this workflow
            job_models = await self.postgres.list_jobs_by_workflow(wf_model.id)
            jobs = [
                Job(
                    id=j.id,
                    type=j.type,
                    parameters=j.parameters,
                    status=j.status,
                    worker_id=j.worker_id,
                    result=j.result,
                    error=j.error,
                    retry_count=j.retry_count,
                    max_retries=j.max_retries,
                    on_success=j.on_success,
                    on_failure=j.on_failure,
                    always_run=j.always_run,
                    created_at=j.created_at,
                    updated_at=j.updated_at,
                ) for j in job_models
            ]

            # Reconstruct workflow
            workflow = Workflow(
                id=wf_model.id,
                name=wf_model.name,
                status=wf_model.status,
                jobs=jobs,
                current_jobs=wf_model.current_jobs,
                completed_jobs=wf_model.completed_jobs,
                failed_jobs=wf_model.failed_jobs,
                created_at=wf_model.created_at,
                updated_at=wf_model.updated_at,
            )

            # Add to memory
            self.workflows[workflow.id] = workflow
            for job in jobs:
                self.jobs[job.id] = job

        # Load all workers
        worker_models = await self.postgres.list_workers()
        for w_model in worker_models:
            worker = Worker(
                id=w_model.id,
                status=w_model.status,
                capabilities=[JobType(cap) for cap in w_model.capabilities],
                current_job_id=w_model.current_job_id,
                last_heartbeat=w_model.last_heartbeat,
                registered_at=w_model.registered_at,
            )
            self.workers[worker.id] = worker

        # Load all job assignments
        assignment_models = await self.postgres.list_all_assignments()
        for assignment in assignment_models:
            self.job_assignments[assignment.job_id] = assignment.worker_id

    # Async methods (for new code or when DB persistence is needed)
    async def get_workflow_async(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow from cache or DB (async version)"""
        # Try in-memory first
        if workflow_id in self.workflows:
            return self.workflows[workflow_id]

        # Try Redis cache
        if self.redis:
            cached = await self.redis.get_cached_workflow(workflow_id)
            if cached:
                workflow = Workflow(**cached)
                self.workflows[workflow_id] = workflow
                return workflow

        # Try PostgreSQL
        if self.postgres:
            model = await self.postgres.get_workflow(workflow_id)
            if model:
                # Reconstruct Workflow with jobs
                job_models = await self.postgres.list_jobs_by_workflow(
                    workflow_id)
                jobs = [
                    Job(
                        id=j.id,
                        type=j.type,
                        parameters=j.parameters,
                        status=j.status,
                        worker_id=j.worker_id,
                        result=j.result,
                        error=j.error,
                        retry_count=j.retry_count,
                        max_retries=j.max_retries,
                        on_success=j.on_success,
                        on_failure=j.on_failure,
                        always_run=j.always_run,
                        created_at=j.created_at,
                        updated_at=j.updated_at,
                    ) for j in job_models
                ]
                workflow = Workflow(
                    id=model.id,
                    name=model.name,
                    status=model.status,
                    jobs=jobs,
                    current_jobs=model.current_jobs,
                    completed_jobs=model.completed_jobs,
                    failed_jobs=model.failed_jobs,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )
                # Cache it
                self.workflows[workflow_id] = workflow
                for job in jobs:
                    self.jobs[job.id] = job
                return workflow

        return None

    async def add_workflow_async(self, workflow: Workflow) -> None:
        """Add workflow to memory and persist (async version)"""
        self.workflows[workflow.id] = workflow

        # Add jobs to memory
        for job in workflow.jobs:
            self.jobs[job.id] = job

        # Persist to DB
        if self.postgres:
            await self.postgres.save_workflow(workflow)
            for job in workflow.jobs:
                await self.postgres.save_job(job, workflow.id)

        # Cache in Redis
        if self.redis:
            await self.redis.cache_workflow(workflow)
            for job in workflow.jobs:
                await self.redis.cache_job(job)


# Global state instance
_state: Optional[StateManager] = None


def state_manager() -> StateManager:
    """Dependency injection function for FastAPI"""
    global _state
    if _state is None:
        _state = StateManager()
    return _state


async def init_state_manager(database_url: Optional[str] = None,
                             redis_url: Optional[str] = None) -> StateManager:
    """Initialize state manager with database backends"""
    global _state

    postgres = None
    redis_cache = None

    if database_url:
        postgres = PostgresDB(database_url)
        await postgres.init_db()

    if redis_url:
        redis_cache = RedisCache(redis_url)
        await redis_cache.connect()

    _state = StateManager(postgres=postgres, redis=redis_cache)
    
    # Rebuild in-memory cache from database after restart
    if postgres:
        await _state._rebuild_from_db()
    
    return _state
