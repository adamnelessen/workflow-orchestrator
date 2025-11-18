"""Unit tests for WorkflowEngine"""
import asyncio
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from coordinator.core.workflow_engine import WorkflowEngine
from coordinator.core.state_manager import StateManager
from shared.models import Workflow, Job, Worker
from shared.enums import JobType, JobStatus, WorkflowStatus

# ============================================================================
# Dependency Graph Tests
# ============================================================================


@pytest.mark.unit
def test_build_dependency_graph_simple(workflow_engine: WorkflowEngine,
                                       simple_workflow: Workflow) -> None:
    """Test building dependency graph for simple linear workflow"""
    deps = workflow_engine._build_dependency_graph(simple_workflow)

    # job1 has no dependencies (entry point)
    assert deps["job1"] == set()
    # job2 depends on job1 (via on_success)
    assert deps["job2"] == {"job1"}


@pytest.mark.unit
def test_build_dependency_graph_branching(
        workflow_engine: WorkflowEngine, branching_workflow: Workflow) -> None:
    """Test building dependency graph for branching workflow"""
    deps = workflow_engine._build_dependency_graph(branching_workflow)

    # job1 is the entry point
    assert deps["job1"] == set()
    # job2 and job3 both depend on job1
    assert deps["job2"] == {"job1"}
    assert deps["job3"] == {"job1"}


@pytest.mark.unit
def test_validate_circular_dependency(workflow_engine: WorkflowEngine) -> None:
    """Test detection of circular dependencies"""
    now = datetime.now(UTC)
    jobs = [
        Job(id="job1",
            type=JobType.VALIDATION,
            parameters={},
            on_success=["job2"],
            created_at=now,
            updated_at=now),
        Job(id="job2",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["job1"],
            created_at=now,
            updated_at=now),  # Circular!
    ]
    workflow = Workflow(id="circular",
                        name="circular-workflow",
                        status=WorkflowStatus.PENDING,
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    with pytest.raises(ValueError, match="Circular dependency detected"):
        workflow_engine._build_dependency_graph(workflow)


@pytest.mark.unit
def test_validate_invalid_job_reference(
        workflow_engine: WorkflowEngine) -> None:
    """Test detection of invalid job references"""
    now = datetime.now(UTC)
    jobs = [
        Job(id="job1",
            type=JobType.VALIDATION,
            parameters={},
            on_success=["nonexistent"],
            created_at=now,
            updated_at=now),
    ]
    workflow = Workflow(id="invalid",
                        name="invalid-workflow",
                        status=WorkflowStatus.PENDING,
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    with pytest.raises(ValueError, match="non-existent on_success job"):
        workflow_engine._build_dependency_graph(workflow)


@pytest.mark.unit
def test_find_entry_jobs(workflow_engine: WorkflowEngine,
                         simple_workflow: Workflow) -> None:
    """Test finding entry jobs (jobs with no dependencies)"""
    deps = workflow_engine._build_dependency_graph(simple_workflow)
    entry_jobs = workflow_engine._find_entry_jobs(deps)

    assert entry_jobs == ["job1"]


# ============================================================================
# Workflow Start Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_workflow_success(workflow_engine: WorkflowEngine,
                                      state_manager: StateManager,
                                      simple_workflow: Workflow,
                                      mock_worker: Worker) -> None:
    """Test starting a workflow successfully"""
    # Add workflow and jobs to state
    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    # Mock scheduler to simulate successful assignment
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    success = await workflow_engine.start_workflow(simple_workflow.id)

    assert success is True
    assert simple_workflow.status == WorkflowStatus.RUNNING
    assert "job1" in simple_workflow.current_jobs


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_workflow_not_found(
        workflow_engine: WorkflowEngine) -> None:
    """Test starting a non-existent workflow"""
    success = await workflow_engine.start_workflow("nonexistent")
    assert success is False


@pytest.mark.unit
@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_workflow_already_running(
        workflow_engine: WorkflowEngine, state_manager: StateManager,
        simple_workflow: Workflow) -> None:
    """Test starting a workflow that's already running"""
    simple_workflow.status = WorkflowStatus.RUNNING
    await state_manager.add_workflow(simple_workflow)

    success = await workflow_engine.start_workflow(simple_workflow.id)
    assert success is False


# ============================================================================
# Job Completion Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_job_completion_triggers_next(
        workflow_engine: WorkflowEngine, state_manager: StateManager,
        simple_workflow: Workflow, mock_worker: Worker) -> None:
    """Test that completing a job triggers the next job"""
    # Setup workflow in running state
    simple_workflow.status = WorkflowStatus.RUNNING
    simple_workflow.current_jobs = ["job1"]
    simple_workflow.jobs[0].status = JobStatus.RUNNING

    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    # Build dependency cache
    workflow_engine._dependency_cache[simple_workflow.id] = \
        workflow_engine._build_dependency_graph(simple_workflow)

    # Mock scheduler
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Complete job1
    await workflow_engine.handle_job_completion("job1", {"result": "success"})

    # Check job1 is marked completed
    job1 = await state_manager.get_job("job1")
    assert job1.status == JobStatus.COMPLETED
    assert "job1" in simple_workflow.completed_jobs

    # Check job2 was scheduled
    assert workflow_engine.scheduler.assign_job.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_job_completion_workflow_completes(
        workflow_engine: WorkflowEngine, state_manager: StateManager,
        simple_workflow: Workflow) -> None:
    """Test workflow completion when last job finishes"""
    # Setup workflow with job1 completed and job2 running
    simple_workflow.status = WorkflowStatus.RUNNING
    simple_workflow.current_jobs = ["job2"]
    simple_workflow.completed_jobs = ["job1"]
    simple_workflow.jobs[0].status = JobStatus.COMPLETED
    simple_workflow.jobs[1].status = JobStatus.RUNNING

    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[simple_workflow.id] = \
        workflow_engine._build_dependency_graph(simple_workflow)

    # Complete job2 (last job)
    await workflow_engine.handle_job_completion("job2", {"result": "success"})

    # Workflow should be completed
    assert simple_workflow.status == WorkflowStatus.COMPLETED
    assert "job2" in simple_workflow.completed_jobs
    assert len(simple_workflow.current_jobs) == 0


# ============================================================================
# Job Failure Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_job_failure_retry(workflow_engine: WorkflowEngine,
                                        state_manager: StateManager,
                                        simple_workflow: Workflow,
                                        mock_worker: Worker) -> None:
    """Test job retry on failure"""
    # Setup
    simple_workflow.status = WorkflowStatus.RUNNING
    simple_workflow.current_jobs = ["job1"]
    simple_workflow.jobs[0].status = JobStatus.RUNNING
    simple_workflow.jobs[0].max_retries = 3
    simple_workflow.jobs[0].retry_count = 0

    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[simple_workflow.id] = \
        workflow_engine._build_dependency_graph(simple_workflow)

    # Mock scheduler
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Fail job1
    await workflow_engine.handle_job_failure("job1", {"message": "Test error"})

    # Check job was retried
    job1 = await state_manager.get_job("job1")
    assert job1.status == JobStatus.RUNNING  # Rescheduled, so back to RUNNING
    assert job1.retry_count == 1
    assert workflow_engine.scheduler.assign_job.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_job_failure_max_retries(workflow_engine: WorkflowEngine,
                                              state_manager: StateManager,
                                              branching_workflow: Workflow,
                                              mock_worker: Worker) -> None:
    """Test job failure after max retries triggers failure path"""
    # Setup
    branching_workflow.status = WorkflowStatus.RUNNING
    branching_workflow.current_jobs = ["job1"]
    branching_workflow.jobs[0].status = JobStatus.RUNNING
    branching_workflow.jobs[0].max_retries = 2
    branching_workflow.jobs[0].retry_count = 2  # Already at max

    await state_manager.add_workflow(branching_workflow)
    for job in branching_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[branching_workflow.id] = \
        workflow_engine._build_dependency_graph(branching_workflow)

    # Mock scheduler
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Fail job1
    await workflow_engine.handle_job_failure("job1", {"message": "Test error"})

    # Check job is failed
    job1 = await state_manager.get_job("job1")
    assert job1.status == JobStatus.FAILED
    assert "job1" in branching_workflow.failed_jobs

    # Check failure handler (job3) was scheduled
    assert workflow_engine.scheduler.assign_job.called


# ============================================================================
# Always Run Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_always_run_jobs_on_failure(workflow_engine: WorkflowEngine,
                                          state_manager: StateManager,
                                          branching_workflow: Workflow,
                                          mock_worker: Worker) -> None:
    """Test that always_run jobs execute even when workflow fails"""
    # Setup workflow with failed job
    branching_workflow.status = WorkflowStatus.RUNNING
    branching_workflow.failed_jobs = ["job1"]
    branching_workflow.jobs[0].status = JobStatus.FAILED

    await state_manager.add_workflow(branching_workflow)
    for job in branching_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[branching_workflow.id] = \
        workflow_engine._build_dependency_graph(branching_workflow)

    # Mock scheduler
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Trigger workflow failure
    await workflow_engine._fail_workflow(branching_workflow)

    # Check always_run job was scheduled
    assert workflow_engine.scheduler.assign_job.called


# ============================================================================
# Workflow Cancellation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_workflow(workflow_engine: WorkflowEngine,
                               state_manager: StateManager,
                               simple_workflow: Workflow,
                               mock_worker: Worker) -> None:
    """Test cancelling a running workflow"""
    # Setup running workflow
    simple_workflow.status = WorkflowStatus.RUNNING
    simple_workflow.current_jobs = ["job1"]
    simple_workflow.jobs[0].status = JobStatus.RUNNING

    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[simple_workflow.id] = \
        workflow_engine._build_dependency_graph(simple_workflow)

    # Cancel workflow
    success = await workflow_engine.cancel_workflow(simple_workflow.id)

    assert success is True
    assert simple_workflow.status == WorkflowStatus.CANCELLED

    # Running jobs should be marked as failed
    job1 = await state_manager.get_job("job1")
    assert job1.status == JobStatus.FAILED
    assert job1.error == "Workflow cancelled"


# ============================================================================
# Helper Method Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_can_schedule_job(workflow_engine: WorkflowEngine,
                          state_manager: StateManager,
                          simple_workflow: Workflow) -> None:
    """Test checking if a job can be scheduled"""
    await state_manager.add_workflow(simple_workflow)
    for job in simple_workflow.jobs:
        await state_manager.add_job(job)

    workflow_engine._dependency_cache[simple_workflow.id] = \
        workflow_engine._build_dependency_graph(simple_workflow)

    # job1 has no dependencies, can be scheduled
    can_schedule = workflow_engine._can_schedule_job(simple_workflow, "job1")
    assert can_schedule is True

    # job2 depends on job1, cannot be scheduled yet
    can_schedule = workflow_engine._can_schedule_job(simple_workflow, "job2")
    assert can_schedule is False

    # Mark job1 completed
    simple_workflow.completed_jobs.append("job1")

    # Now job2 can be scheduled
    can_schedule = workflow_engine._can_schedule_job(simple_workflow, "job2")
    assert can_schedule is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_workflow_for_job(workflow_engine: WorkflowEngine,
                               state_manager: StateManager,
                               simple_workflow: Workflow) -> None:
    """Test finding workflow containing a specific job"""
    await state_manager.add_workflow(simple_workflow)

    workflow = workflow_engine._find_workflow_for_job("job1")
    assert workflow is not None
    assert workflow.id == simple_workflow.id

    workflow = workflow_engine._find_workflow_for_job("nonexistent")
    assert workflow is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_job_status(workflow_engine: WorkflowEngine,
                           state_manager: StateManager,
                           simple_workflow: Workflow) -> None:
    """Test updating job status"""
    await state_manager.add_job(simple_workflow.jobs[0])

    await workflow_engine.update_job_status("job1", JobStatus.RUNNING.value)

    job = await state_manager.get_job("job1")
    assert job.status == JobStatus.RUNNING


# ============================================================================
# Skipped Jobs Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_failure_jobs_marked_as_skipped(
        workflow_engine: WorkflowEngine, state_manager: StateManager) -> None:
    """Test that on_failure jobs are marked as SKIPPED when workflow succeeds"""
    now = datetime.now(UTC)

    jobs = [
        Job(id="main-job",
            type=JobType.PROCESSING,
            parameters={},
            on_success=["success-handler"],
            on_failure=["failure-handler"],
            created_at=now,
            updated_at=now),
        Job(id="success-handler",
            type=JobType.INTEGRATION,
            parameters={},
            created_at=now,
            updated_at=now),
        Job(id="failure-handler",
            type=JobType.CLEANUP,
            parameters={},
            created_at=now,
            updated_at=now),
    ]

    workflow = Workflow(id="skip-test",
                        name="Skip Test",
                        jobs=jobs,
                        created_at=now,
                        updated_at=now)

    await state_manager.add_workflow(workflow)
    for job in workflow.jobs:
        await state_manager.add_job(job)

    # Mock scheduler to simulate successful assignment
    workflow_engine.scheduler.assign_job = AsyncMock(return_value="worker1")

    # Start workflow - should schedule main-job
    await workflow_engine.start_workflow(workflow.id)
    assert workflow.status == WorkflowStatus.RUNNING
    assert "main-job" in workflow.current_jobs

    # Complete main-job successfully - should schedule success-handler, not failure-handler
    await workflow_engine.handle_job_completion("main-job",
                                                {"status": "success"})
    assert "success-handler" in workflow.current_jobs
    assert "failure-handler" not in workflow.current_jobs

    # failure-handler should still be PENDING at this point
    failure_job = await state_manager.get_job("failure-handler")
    assert failure_job.status == JobStatus.PENDING

    # Complete success-handler
    await workflow_engine.handle_job_completion("success-handler",
                                                {"status": "success"})

    # Workflow should be completed
    assert workflow.status == WorkflowStatus.COMPLETED

    # failure-handler should now be SKIPPED (not PENDING)
    failure_job = await state_manager.get_job("failure-handler")
    assert failure_job.status == JobStatus.SKIPPED
    assert "failure-handler" not in workflow.completed_jobs
    assert "failure-handler" not in workflow.failed_jobs
