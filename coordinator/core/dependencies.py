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
        _worker_registry = WorkerRegistry(state)
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
        _workflow_engine = WorkflowEngine(get_worker_registry())
    return _workflow_engine
