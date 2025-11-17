"""PostgreSQL database connection and operations"""
import os
from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import update, delete

from coordinator.db.models import Base, WorkflowModel, JobModel, WorkerModel, JobAssignmentModel
from shared.models import Workflow, Job, Worker


class PostgresDB:
    """PostgreSQL database manager"""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url,
                                          echo=False,
                                          pool_pre_ping=True)
        self.async_session = async_sessionmaker(self.engine,
                                                class_=AsyncSession,
                                                expire_on_commit=False)

    async def init_db(self):
        """Initialize database schema"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

    # Workflow operations
    async def save_workflow(self, workflow: Workflow) -> None:
        """Save or update a workflow"""
        async with self.async_session() as session:
            model = WorkflowModel(
                id=workflow.id,
                name=workflow.name,
                status=workflow.status,
                current_jobs=workflow.current_jobs,
                completed_jobs=workflow.completed_jobs,
                failed_jobs=workflow.failed_jobs,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at,
            )
            await session.merge(model)
            await session.commit()

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowModel]:
        """Get a workflow by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkflowModel).where(WorkflowModel.id == workflow_id))
            return result.scalar_one_or_none()

    async def list_workflows(self) -> List[WorkflowModel]:
        """List all workflows"""
        async with self.async_session() as session:
            result = await session.execute(select(WorkflowModel))
            return list(result.scalars().all())

    async def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow"""
        async with self.async_session() as session:
            await session.execute(
                delete(WorkflowModel).where(WorkflowModel.id == workflow_id))
            await session.commit()

    # Job operations
    async def save_job(self, job: Job, workflow_id: str) -> None:
        """Save or update a job"""
        async with self.async_session() as session:
            model = JobModel(
                id=job.id,
                workflow_id=workflow_id,
                type=job.type,
                parameters=job.parameters,
                status=job.status,
                worker_id=job.worker_id,
                result=job.result,
                error=job.error,
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                on_success=job.on_success,
                on_failure=job.on_failure,
                always_run=job.always_run,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            await session.merge(model)
            await session.commit()

    async def get_job(self, job_id: str) -> Optional[JobModel]:
        """Get a job by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(JobModel).where(JobModel.id == job_id))
            return result.scalar_one_or_none()

    async def list_jobs_by_workflow(self, workflow_id: str) -> List[JobModel]:
        """List all jobs for a workflow"""
        async with self.async_session() as session:
            result = await session.execute(
                select(JobModel).where(JobModel.workflow_id == workflow_id))
            return list(result.scalars().all())

    # Worker operations
    async def save_worker(self, worker: Worker) -> None:
        """Save or update a worker"""
        async with self.async_session() as session:
            model = WorkerModel(
                id=worker.id,
                status=worker.status,
                capabilities=[cap.value for cap in worker.capabilities],
                current_job_id=worker.current_job_id,
                last_heartbeat=worker.last_heartbeat,
                registered_at=worker.registered_at,
            )
            await session.merge(model)
            await session.commit()

    async def get_worker(self, worker_id: str) -> Optional[WorkerModel]:
        """Get a worker by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkerModel).where(WorkerModel.id == worker_id))
            return result.scalar_one_or_none()

    async def list_workers(self) -> List[WorkerModel]:
        """List all workers"""
        async with self.async_session() as session:
            result = await session.execute(select(WorkerModel))
            return list(result.scalars().all())

    async def delete_worker(self, worker_id: str) -> None:
        """Delete a worker"""
        async with self.async_session() as session:
            await session.execute(
                delete(WorkerModel).where(WorkerModel.id == worker_id))
            await session.commit()

    # Job assignment operations
    async def save_assignment(self, job_id: str, worker_id: str) -> None:
        """Save a job assignment"""
        async with self.async_session() as session:
            model = JobAssignmentModel(job_id=job_id, worker_id=worker_id)
            await session.merge(model)
            await session.commit()

    async def get_assignment(self, job_id: str) -> Optional[str]:
        """Get worker ID for a job"""
        async with self.async_session() as session:
            result = await session.execute(
                select(JobAssignmentModel).where(
                    JobAssignmentModel.job_id == job_id))
            assignment = result.scalar_one_or_none()
            return assignment.worker_id if assignment else None

    async def delete_assignment(self, job_id: str) -> None:
        """Delete a job assignment"""
        async with self.async_session() as session:
            await session.execute(
                delete(JobAssignmentModel).where(
                    JobAssignmentModel.job_id == job_id))
            await session.commit()
