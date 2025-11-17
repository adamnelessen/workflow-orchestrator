"""Dependency injection and singleton initialization"""
from coordinator.core.state_manager import state_manager
from coordinator.core.worker_registry import WorkerRegistry
from coordinator.core.scheduler import Scheduler

# Singletons - initialized once on startup
_worker_registry = None
_scheduler = None
_workflow_engine = None


def get_worker_registry() -> WorkerRegistry:
    """Get or create WorkerRegistry singleton"""
    global _worker_registry
    if _worker_registry is None:
        state = state_manager()
        # Initialize without workflow_engine first to avoid circular dependency
        _worker_registry = WorkerRegistry(state, None)
        # Set workflow_engine after it's created
        if _workflow_engine is not None:
            _worker_registry.workflow_engine = _workflow_engine
    return _worker_registry


def get_scheduler() -> Scheduler:
    """Get or create Scheduler singleton"""
    global _scheduler
    if _scheduler is None:
        state = state_manager()
        _scheduler = Scheduler(state)
    return _scheduler


def get_workflow_engine():
    """Get or create WorkflowEngine singleton"""
    from coordinator.core.workflow_engine import WorkflowEngine

    global _workflow_engine
    if _workflow_engine is None:
        state = state_manager()
        scheduler = get_scheduler()
        _workflow_engine = WorkflowEngine(state, scheduler)
        # Now that workflow engine is created, set it on the worker registry
        worker_registry = get_worker_registry()
        worker_registry.workflow_engine = _workflow_engine
    return _workflow_engine
