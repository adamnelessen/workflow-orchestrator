"""Example: Using PostgreSQL and Redis for persistent workflows

This example demonstrates how to leverage the new database backends
for workflow persistence and recovery.
"""
import asyncio
from datetime import datetime, UTC
from coordinator.core.state_manager import init_state_manager
from shared.models import Workflow, Job
from shared.enums import JobStatus, JobType, WorkflowStatus


async def main():
    # Initialize state manager with PostgreSQL and Redis
    state = await init_state_manager(
        database_url=
        "postgresql+psycopg://workflow:workflow_dev@localhost:5432/workflow_orchestrator",
        redis_url="redis://localhost:6379/0")

    print("✅ Connected to PostgreSQL and Redis\n")

    # Create a workflow
    workflow = Workflow(
        id="demo-workflow-001",
        name="Database Demo Workflow",
        status=WorkflowStatus.PENDING,
        jobs=[
            Job(
                id="job-1",
                type=JobType.VALIDATION,
                parameters={"data": "test"},
                status=JobStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Job(
                id="job-2",
                type=JobType.PROCESSING,
                parameters={"process": "data"},
                status=JobStatus.PENDING,
                on_success=["job-1"],  # Depends on job-1
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Persist workflow (writes to PostgreSQL + Redis)
    print(f"💾 Saving workflow: {workflow.id}")
    await state.add_workflow_async(workflow)
    print("✅ Workflow saved to PostgreSQL and cached in Redis\n")

    # Simulate crash - clear in-memory state
    print("💥 Simulating coordinator crash (clearing memory)...")
    state.workflows.clear()
    state.jobs.clear()
    print("✅ Memory cleared\n")

    # Recover from database
    print(f"🔄 Recovering workflow from database...")
    recovered = await state.get_workflow_async(workflow.id)

    if recovered:
        print(f"✅ Workflow recovered successfully!")
        print(f"   ID: {recovered.id}")
        print(f"   Name: {recovered.name}")
        print(f"   Status: {recovered.status}")
        print(f"   Jobs: {len(recovered.jobs)}")
        for job in recovered.jobs:
            print(f"      - {job.id} ({job.type.value})")
    else:
        print("❌ Failed to recover workflow")

    print("\n🎉 Database persistence working correctly!")

    # Check Redis cache
    if state.redis:
        queue_len = await state.redis.queue_length()
        print(f"\n📊 Redis metrics:")
        print(f"   Job queue length: {queue_len}")

        # Add a job to the queue
        await state.redis.push_job("test-job", priority=1)
        queue_len = await state.redis.queue_length()
        print(f"   After adding job: {queue_len}")

        # Pop the job
        job_id = await state.redis.pop_job()
        print(f"   Popped job: {job_id}")


if __name__ == "__main__":
    print("🚀 Database Persistence Demo\n")
    print("Make sure PostgreSQL and Redis are running:")
    print("  docker-compose up postgres redis\n")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure databases are running:")
        print("  docker-compose up postgres redis")
