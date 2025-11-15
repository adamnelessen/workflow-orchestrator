from coordinator.core.worker_registry import WorkerRegistry


class WorkflowEngine:

    def __init__(self, worker_registry: WorkerRegistry):
        self.ws_manager = worker_registry

    def handle_job_completion(self, job_id: str, result: dict):
        # Logic to update workflow and job status upon job completion
        pass

    def handle_job_failure(self, job_id: str, result: dict):
        # Logic to update workflow and job status upon job failure
        pass

    def update_job_status(self, job_id: str, status: str):
        # Logic to update job status
        pass


# Initialize singleton with dependency injection
_workflow_engine = None


def get_workflow_engine() -> WorkflowEngine:
    """Get or create WorkflowEngine singleton"""
    global _workflow_engine
    if _workflow_engine is None:
        from coordinator.core.dependencies import get_worker_registry
        _workflow_engine = WorkflowEngine(get_worker_registry())
    return _workflow_engine
