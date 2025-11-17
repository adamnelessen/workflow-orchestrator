"""Workflow engine for orchestrating job execution and managing workflow state"""
import logging
from typing import Dict, Set, List, Optional
from datetime import datetime, UTC

from coordinator.core.state_manager import StateManager
from coordinator.core.scheduler import Scheduler
from shared.models import Workflow, Job
from shared.enums import JobStatus, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Main workflow orchestrator that manages workflow execution and job dependencies"""

    def __init__(self, state_manager: StateManager, scheduler: Scheduler):
        self.state = state_manager
        self.scheduler = scheduler
        # Cache for workflow dependency graphs
        self._dependency_cache: Dict[str, Dict[str, Set[str]]] = {}

    # ========================================================================
    # Workflow Initialization
    # ========================================================================

    async def start_workflow(self, workflow_id: str) -> bool:
        """Start a workflow by scheduling its initial jobs.
        
        Args:
            workflow_id: The workflow to start
            
        Returns:
            bool: True if workflow started successfully, False otherwise
        """
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        if workflow.status != WorkflowStatus.PENDING:
            logger.warning(f"Workflow {workflow_id} is not in PENDING state")
            return False

        try:
            # Build dependency graph and validate
            dependencies = self._build_dependency_graph(workflow)
            self._dependency_cache[workflow_id] = dependencies

            # Find entry jobs (jobs with no dependencies)
            entry_jobs = self._find_entry_jobs(dependencies)

            if not entry_jobs:
                logger.error(f"No entry jobs found for workflow {workflow_id}")
                workflow.status = WorkflowStatus.FAILED
                workflow.updated_at = datetime.now(UTC)
                return False

            # Update workflow status
            workflow.status = WorkflowStatus.RUNNING
            workflow.updated_at = datetime.now(UTC)

            # Schedule entry jobs
            for job_id in entry_jobs:
                await self._schedule_job(workflow_id, job_id)

            logger.info(
                f"Started workflow {workflow_id} with {len(entry_jobs)} entry jobs"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting workflow {workflow_id}: {e}")
            workflow.status = WorkflowStatus.FAILED
            workflow.updated_at = datetime.now(UTC)
            return False

    def _build_dependency_graph(self,
                                workflow: Workflow) -> Dict[str, Set[str]]:
        """Build a dependency graph for the workflow.
        
        Returns a dict mapping job_id -> set of job_ids it depends on.
        For workflows with on_success/on_failure, dependencies are implicit:
        a job depends on the jobs that reference it in their on_success/on_failure.
        """
        dependencies: Dict[str, Set[str]] = {
            job.id: set()
            for job in workflow.jobs
        }

        # Validate: check all referenced jobs exist
        job_ids = {job.id for job in workflow.jobs}
        for job in workflow.jobs:
            # Validate on_success references (always a list)
            if job.on_success:
                for ref in job.on_success:
                    if ref not in job_ids:
                        raise ValueError(
                            f"Job {job.id} references non-existent on_success job: {ref}"
                        )

            # Validate on_failure references (always a list)
            if job.on_failure:
                for ref in job.on_failure:
                    if ref not in job_ids:
                        raise ValueError(
                            f"Job {job.id} references non-existent on_failure job: {ref}"
                        )

        # Build reverse dependencies from on_success and on_failure
        for job in workflow.jobs:
            # Handle on_success (always a list)
            if job.on_success:
                for ref in job.on_success:
                    dependencies[ref].add(job.id)

            # Handle on_failure (always a list)
            if job.on_failure:
                for ref in job.on_failure:
                    dependencies[ref].add(job.id)

        # Validate: check for cycles
        self._validate_no_cycles(dependencies)

        return dependencies

    def _validate_no_cycles(self, dependencies: Dict[str, Set[str]]) -> None:
        """Check for circular dependencies using DFS."""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for job_id in dependencies:
            if job_id not in visited:
                if has_cycle(job_id):
                    raise ValueError(
                        f"Circular dependency detected in workflow involving job: {job_id}"
                    )

    def _find_entry_jobs(self, dependencies: Dict[str, Set[str]]) -> List[str]:
        """Find jobs with no dependencies (entry points)."""
        return [job_id for job_id, deps in dependencies.items() if not deps]

    # ========================================================================
    # Job Completion Handling
    # ========================================================================

    async def handle_job_completion(self, job_id: str, result: dict) -> None:
        """Handle successful job completion and trigger next jobs.
        
        Args:
            job_id: The completed job ID
            result: Job execution result
        """
        job = self.state.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Update job status
        job.status = JobStatus.COMPLETED
        job.result = result
        job.updated_at = datetime.now(UTC)

        logger.info(f"Job {job_id} completed successfully")

        # Find workflow containing this job
        workflow = self._find_workflow_for_job(job_id)
        if not workflow:
            logger.error(f"No workflow found for job {job_id}")
            return

        # Add to completed jobs
        if job_id not in workflow.completed_jobs:
            workflow.completed_jobs.append(job_id)

        # Remove from current jobs
        if job_id in workflow.current_jobs:
            workflow.current_jobs.remove(job_id)

        workflow.updated_at = datetime.now(UTC)

        # Schedule next jobs based on on_success (always a list)
        if job.on_success:
            for next_job_id in job.on_success:
                if self._can_schedule_job(workflow, next_job_id):
                    await self._schedule_job(workflow.id, next_job_id)

        # Check if workflow is complete
        await self._check_workflow_completion(workflow)

    # ========================================================================
    # Job Failure Handling
    # ========================================================================

    async def handle_job_failure(self, job_id: str, error: dict) -> None:
        """Handle job failure, retry logic, and failure paths.
        
        Args:
            job_id: The failed job ID
            error: Error information
        """
        job = self.state.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        logger.warning(f"Job {job_id} failed: {error}")

        # Check retry logic
        if job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = JobStatus.RETRYING
            job.error = error.get("message", "Unknown error")
            job.updated_at = datetime.now(UTC)
            job.worker_id = None

            logger.info(
                f"Retrying job {job_id} (attempt {job.retry_count}/{job.max_retries})"
            )

            # Find workflow and reschedule
            workflow = self._find_workflow_for_job(job_id)
            if workflow:
                await self._schedule_job(workflow.id, job_id)
            return

        # Max retries exceeded
        job.status = JobStatus.FAILED
        job.error = error.get("message", "Unknown error")
        job.updated_at = datetime.now(UTC)

        logger.error(f"Job {job_id} failed after {job.retry_count} retries")

        # Find workflow
        workflow = self._find_workflow_for_job(job_id)
        if not workflow:
            logger.error(f"No workflow found for job {job_id}")
            return

        # Add to failed jobs
        if job_id not in workflow.failed_jobs:
            workflow.failed_jobs.append(job_id)

        # Remove from current jobs
        if job_id in workflow.current_jobs:
            workflow.current_jobs.remove(job_id)

        workflow.updated_at = datetime.now(UTC)

        # Schedule failure handler if specified (always a list)
        if job.on_failure:
            for next_job_id in job.on_failure:
                if self._can_schedule_job(workflow, next_job_id):
                    await self._schedule_job(workflow.id, next_job_id)
        else:
            # No failure handler, workflow fails
            await self._fail_workflow(workflow)

    # ========================================================================
    # Workflow Completion
    # ========================================================================

    async def _check_workflow_completion(self, workflow: Workflow) -> None:
        """Check if workflow is complete and update status accordingly."""
        # Workflow is still running if there are current jobs
        if workflow.current_jobs:
            return

        # Check if there are any more jobs that can be scheduled
        can_schedule_more = False

        for job in workflow.jobs:
            if job.id not in workflow.completed_jobs and job.id not in workflow.failed_jobs:
                # Skip always_run jobs - they're handled separately in _run_always_run_jobs
                if job.always_run:
                    continue
                if self._can_schedule_job(workflow, job.id):
                    can_schedule_more = True
                    break

        if not can_schedule_more:
            # Mark unexecuted jobs as skipped (e.g., on_failure jobs in successful workflows)
            await self._mark_skipped_jobs(workflow)

            # Run always_run jobs before completing
            await self._run_always_run_jobs(workflow)

            # Determine final status
            if workflow.failed_jobs:
                workflow.status = WorkflowStatus.FAILED
                logger.info(
                    f"Workflow {workflow.id} failed with {len(workflow.failed_jobs)} failed jobs"
                )
            else:
                workflow.status = WorkflowStatus.COMPLETED
                logger.info(f"Workflow {workflow.id} completed successfully")

            workflow.updated_at = datetime.now(UTC)

            # Clean up cache
            self._dependency_cache.pop(workflow.id, None)

    async def _fail_workflow(self, workflow: Workflow) -> None:
        """Mark workflow as failed and run cleanup jobs."""
        workflow.status = WorkflowStatus.FAILED
        workflow.updated_at = datetime.now(UTC)

        logger.error(f"Workflow {workflow.id} failed")

        # Run always_run cleanup jobs
        await self._run_always_run_jobs(workflow)

        # Clean up cache
        self._dependency_cache.pop(workflow.id, None)

    async def _run_always_run_jobs(self, workflow: Workflow) -> None:
        """Execute all jobs marked as always_run."""
        always_run_jobs = [
            job for job in workflow.jobs if job.always_run
            and job.status not in [JobStatus.COMPLETED, JobStatus.RUNNING]
        ]

        if always_run_jobs:
            logger.info(
                f"Running {len(always_run_jobs)} always_run cleanup jobs for workflow {workflow.id}"
            )
            for job in always_run_jobs:
                await self._schedule_job(workflow.id, job.id)

    async def _mark_skipped_jobs(self, workflow: Workflow) -> None:
        """Mark jobs that were not executed as SKIPPED.
        
        This typically includes on_failure jobs in successful workflows that
        never ran because their triggering condition was never met.
        """
        for job in workflow.jobs:
            # Skip jobs that already have a final status
            if job.id in workflow.completed_jobs or job.id in workflow.failed_jobs:
                continue

            # Skip always_run jobs - they're handled separately
            if job.always_run:
                continue

            # Skip jobs that are currently running
            if job.status == JobStatus.RUNNING:
                continue

            # Check if this job is only reachable via on_failure paths
            # If the job is in PENDING state and can't be scheduled, it should be marked as skipped
            if job.status == JobStatus.PENDING and not self._can_schedule_job(
                    workflow, job.id):
                job.status = JobStatus.SKIPPED
                job.updated_at = datetime.now(UTC)
                logger.info(
                    f"Marked job {job.id} as SKIPPED in workflow {workflow.id}"
                )

    # ========================================================================
    # Job Scheduling Helpers
    # ========================================================================

    async def _schedule_job(self, workflow_id: str, job_id: str) -> bool:
        """Schedule a job for execution.
        
        Args:
            workflow_id: The workflow ID
            job_id: The job to schedule
            
        Returns:
            bool: True if job was scheduled successfully
        """
        workflow = self.state.get_workflow(workflow_id)
        job = self.state.get_job(job_id)

        if not workflow or not job:
            logger.error(f"Workflow {workflow_id} or job {job_id} not found")
            return False

        # Skip if already running or completed
        if job.status in [JobStatus.RUNNING, JobStatus.COMPLETED]:
            logger.debug(f"Job {job_id} already {job.status.value}, skipping")
            return False

        # Update job status
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)

        # Add to workflow's current jobs
        if job_id not in workflow.current_jobs:
            workflow.current_jobs.append(job_id)

        # Assign to worker
        worker_id = await self.scheduler.assign_job(job_id=job_id,
                                                    job_type=job.type.value,
                                                    parameters=job.parameters)

        if worker_id:
            job.worker_id = worker_id
            logger.info(f"Scheduled job {job_id} on worker {worker_id}")
            return True
        else:
            # No workers available - revert status
            job.status = JobStatus.PENDING
            if job_id in workflow.current_jobs:
                workflow.current_jobs.remove(job_id)
            logger.warning(f"No workers available for job {job_id}")
            return False

    def _can_schedule_job(self, workflow: Workflow, job_id: str) -> bool:
        """Check if a job can be scheduled (all dependencies met).
        
        This method checks if a job's dependencies are satisfied based on the 
        actual workflow execution state. For jobs in on_success paths, their
        predecessor must have completed successfully. For jobs in on_failure paths,
        their predecessor must have failed.
        
        Args:
            workflow: The workflow
            job_id: The job to check
            
        Returns:
            bool: True if job can be scheduled
        """
        job = next((j for j in workflow.jobs if j.id == job_id), None)
        if not job:
            return False

        # Don't schedule if already completed or failed
        if job_id in workflow.completed_jobs or job_id in workflow.failed_jobs:
            return False

        # Don't schedule if currently running (unless retrying)
        if job_id in workflow.current_jobs and job.status == JobStatus.RUNNING:
            return False

        # For always_run jobs, they can always be scheduled
        if job.always_run:
            return True

        # Find which jobs reference this job in their on_success or on_failure
        # A job can be scheduled if:
        # 1. It's referenced in on_success of a completed job, OR
        # 2. It's referenced in on_failure of a failed job
        can_schedule = False
        has_predecessors = False

        for predecessor_job in workflow.jobs:
            # Check if this job is in predecessor's on_success
            if predecessor_job.on_success and job_id in predecessor_job.on_success:
                has_predecessors = True
                if predecessor_job.id in workflow.completed_jobs:
                    can_schedule = True
                    break

            # Check if this job is in predecessor's on_failure
            if predecessor_job.on_failure and job_id in predecessor_job.on_failure:
                has_predecessors = True
                if predecessor_job.id in workflow.failed_jobs:
                    can_schedule = True
                    break

        # If no predecessors found, it's an entry job and can be scheduled
        if not has_predecessors:
            can_schedule = True

        logger.debug(
            f"Can schedule job {job_id}: {can_schedule} (has_predecessors: {has_predecessors})"
        )
        return can_schedule

    def _find_workflow_for_job(self, job_id: str) -> Optional[Workflow]:
        """Find the workflow that contains a given job."""
        for workflow in self.state.list_workflows():
            if any(job.id == job_id for job in workflow.jobs):
                return workflow
        return None

    # ========================================================================
    # Workflow Cancellation
    # ========================================================================

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.
        
        Args:
            workflow_id: The workflow to cancel
            
        Returns:
            bool: True if workflow was cancelled successfully
        """
        workflow = self.state.get_workflow(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found")
            return False

        if workflow.status not in [
                WorkflowStatus.RUNNING, WorkflowStatus.PENDING
        ]:
            logger.warning(f"Workflow {workflow_id} is not running or pending")
            return False

        # Update workflow status
        workflow.status = WorkflowStatus.CANCELLED
        workflow.updated_at = datetime.now(UTC)

        # Cancel running jobs (mark as failed)
        for job_id in workflow.current_jobs:
            job = self.state.get_job(job_id)
            if job and job.status == JobStatus.RUNNING:
                job.status = JobStatus.FAILED
                job.error = "Workflow cancelled"
                job.updated_at = datetime.now(UTC)

        logger.info(f"Cancelled workflow {workflow_id}")

        # Run cleanup jobs
        await self._run_always_run_jobs(workflow)

        # Clean up cache
        self._dependency_cache.pop(workflow_id, None)

        return True

    # ========================================================================
    # Job Status Updates
    # ========================================================================

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update the status of a job.
        
        Args:
            job_id: The job ID
            status: The new status (as string)
        """
        job = self.state.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            job.status = JobStatus(status)
            job.updated_at = datetime.now(UTC)
            logger.debug(f"Updated job {job_id} status to {status}")
        except ValueError:
            logger.error(f"Invalid job status: {status}")
