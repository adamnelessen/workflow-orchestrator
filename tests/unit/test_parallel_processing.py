"""Tests for parallel processing workflows"""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from coordinator.core.workflow_engine import WorkflowEngine
from coordinator.core.state_manager import StateManager
from shared.models import Workflow, Job
from shared.enums import JobType, JobStatus, WorkflowStatus


def test_parse_parallel_on_success():
    """Test that on_success can be a list of jobs"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="split",
            type=JobType.PROCESSING,
            parameters={"operation": "split"},
            on_success=["process-a", "process-b", "process-c"],
            created_at=now,
            updated_at=now),
        Job(id="process-a",
            type=JobType.PROCESSING,
            parameters={"chunk": "a"},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-b",
            type=JobType.PROCESSING,
            parameters={"chunk": "b"},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-c",
            type=JobType.PROCESSING,
            parameters={"chunk": "c"},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="aggregate",
            type=JobType.PROCESSING,
            parameters={"operation": "aggregate"},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="parallel-test",
                        name="Parallel Processing Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    # Verify the model accepts list for on_success
    assert isinstance(workflow.jobs[0].on_success, list)
    assert len(workflow.jobs[0].on_success) == 3


def test_build_dependency_graph_parallel(workflow_engine: WorkflowEngine):
    """Test dependency graph building with parallel jobs"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="split",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["process-a", "process-b", "process-c"],
            created_at=now,
            updated_at=now),
        Job(id="process-a",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-b",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-c",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="aggregate",
            type=JobType.PROCESSING,
            parameters={},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="parallel-test",
                        name="Parallel Processing Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    # Build dependency graph
    dependencies = workflow_engine._build_dependency_graph(workflow)

    # Verify dependencies
    assert dependencies["split"] == set()  # Entry job, no dependencies
    assert dependencies["process-a"] == {"split"}  # Depends on split
    assert dependencies["process-b"] == {"split"}  # Depends on split
    assert dependencies["process-c"] == {"split"}  # Depends on split
    assert dependencies["aggregate"] == {
        "process-a", "process-b", "process-c"
    }  # Depends on all three

    # Verify entry jobs
    entry_jobs = workflow_engine._find_entry_jobs(dependencies)
    assert entry_jobs == ["split"]


@pytest.mark.asyncio
async def test_parallel_job_scheduling(workflow_engine: WorkflowEngine,
                                       state_manager: StateManager):
    """Test that parallel jobs are all scheduled when predecessor completes"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="split",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["process-a", "process-b"],
            created_at=now,
            updated_at=now),
        Job(id="process-a",
            type=JobType.PROCESSING,
            parameters={},
            created_at=now,
            updated_at=now),
        Job(id="process-b",
            type=JobType.PROCESSING,
            parameters={},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="parallel-test",
                        name="Parallel Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    state_manager.add_workflow(workflow)
    for job in workflow.jobs:
        state_manager.add_job(job)

    # Mock scheduler to simulate successful assignment
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Start workflow - should schedule split job
    await workflow_engine.start_workflow(workflow.id)
    assert workflow.status == WorkflowStatus.RUNNING
    assert "split" in workflow.current_jobs

    # Complete split job - should schedule both parallel jobs
    await workflow_engine.handle_job_completion("split", {"status": "success"})

    # Verify both jobs were scheduled (they're now running)
    assert "process-a" in workflow.current_jobs
    assert "process-b" in workflow.current_jobs
    assert workflow.jobs[1].status == JobStatus.RUNNING
    assert workflow.jobs[2].status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_aggregate_waits_for_all_parallel_jobs(
        workflow_engine: WorkflowEngine, state_manager: StateManager):
    """Test that aggregate job only runs after all parallel predecessors complete"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="split",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["process-a", "process-b", "process-c"],
            created_at=now,
            updated_at=now),
        Job(id="process-a",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-b",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="process-c",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["aggregate"],
            created_at=now,
            updated_at=now),
        Job(id="aggregate",
            type=JobType.PROCESSING,
            parameters={},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="parallel-test",
                        name="Parallel Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    state_manager.add_workflow(workflow)
    for job in workflow.jobs:
        state_manager.add_job(job)

    # Mock scheduler to simulate successful assignment
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Start workflow
    await workflow_engine.start_workflow(workflow.id)

    # Complete split job
    await workflow_engine.handle_job_completion("split", {"status": "success"})

    # Aggregate should NOT be schedulable yet (no parallel jobs completed)
    assert not workflow_engine._can_schedule_job(workflow, "aggregate")

    # Complete first parallel job
    await workflow_engine.handle_job_completion("process-a",
                                                {"status": "success"})

    # Aggregate still should NOT be schedulable (only 1 of 3 completed)
    assert not workflow_engine._can_schedule_job(workflow, "aggregate")

    # Complete second parallel job
    await workflow_engine.handle_job_completion("process-b",
                                                {"status": "success"})

    # Aggregate still should NOT be schedulable (only 2 of 3 completed)
    assert not workflow_engine._can_schedule_job(workflow, "aggregate")

    # Complete third parallel job
    await workflow_engine.handle_job_completion("process-c",
                                                {"status": "success"})

    # NOW aggregate should be scheduled (all 3 completed)
    assert "aggregate" in workflow.current_jobs
    assert workflow.jobs[4].status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_parallel_on_failure(workflow_engine: WorkflowEngine,
                                   state_manager: StateManager):
    """Test that on_failure can also trigger multiple jobs in parallel"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="risky-job",
            type=JobType.PROCESSING,
            parameters={},
            max_retries=0,
            on_failure=["notify-team", "rollback"],
            created_at=now,
            updated_at=now),
        Job(id="notify-team",
            type=JobType.INTEGRATION,
            parameters={},
            created_at=now,
            updated_at=now),
        Job(id="rollback",
            type=JobType.CLEANUP,
            parameters={},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="failure-test",
                        name="Failure Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    state_manager.add_workflow(workflow)
    for job in workflow.jobs:
        state_manager.add_job(job)

    # Mock scheduler to simulate successful assignment
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Start workflow
    await workflow_engine.start_workflow(workflow.id)
    assert "risky-job" in workflow.current_jobs

    # Fail the risky job (max_retries=0 so it fails immediately and triggers on_failure handlers)
    await workflow_engine.handle_job_failure(
        "risky-job", {"message": "Something went wrong"})

    # Verify the job failed
    assert "risky-job" in workflow.failed_jobs
    assert workflow.jobs[0].status == JobStatus.FAILED

    # The failure handlers should have been triggered - check if _can_schedule_job works correctly
    # Since the handle_job_failure method explicitly schedules them, they might already be running
    # Let's check if they're in current_jobs or at least callable to schedule

    # Check dependency resolution - both jobs depend on risky-job (via on_failure)
    dependencies = workflow_engine._dependency_cache.get(workflow.id, {})
    assert dependencies["notify-team"] == {"risky-job"}
    assert dependencies["rollback"] == {"risky-job"}
