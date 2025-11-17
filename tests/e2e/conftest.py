"""Pytest fixtures for E2E tests."""
import time
import subprocess
import requests
import pytest
from pathlib import Path
from typing import Generator, Dict, Any

from client.workflow_client import WorkflowClient
from shared.enums import WorkflowStatus, JobStatus

# Path to the E2E docker-compose file
E2E_COMPOSE_FILE = Path(__file__).parent / "docker-compose.e2e.yml"
COORDINATOR_URL = "http://localhost:8001"
MAX_STARTUP_WAIT = 60  # seconds


@pytest.fixture(scope="session")
def docker_compose_e2e() -> Generator[None, None, None]:
    """Start and stop docker-compose for E2E tests."""
    print("\n🐳 Starting E2E test environment...")

    # Start docker-compose
    subprocess.run(
        ["docker-compose", "-f",
         str(E2E_COMPOSE_FILE), "up", "-d", "--build"],
        check=True,
        cwd=E2E_COMPOSE_FILE.parent)

    # Wait for services to be healthy
    _wait_for_coordinator()

    print("✓ E2E test environment ready\n")

    yield

    # Teardown - stop and remove containers
    print("\n🧹 Cleaning up E2E test environment...")
    subprocess.run(
        ["docker-compose", "-f",
         str(E2E_COMPOSE_FILE), "down", "-v"],
        check=True,
        cwd=E2E_COMPOSE_FILE.parent)
    print("✓ E2E test environment cleaned up\n")


def _wait_for_coordinator() -> None:
    """Wait for the coordinator to be ready."""
    print(f"⏳ Waiting for coordinator at {COORDINATOR_URL}...")

    start_time = time.time()
    while time.time() - start_time < MAX_STARTUP_WAIT:
        try:
            response = requests.get(f"{COORDINATOR_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Coordinator is healthy")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    raise TimeoutError(
        f"Coordinator did not become healthy within {MAX_STARTUP_WAIT} seconds"
    )


@pytest.fixture(scope="session")
def coordinator_url(docker_compose_e2e: None) -> str:
    """Get the coordinator URL."""
    return COORDINATOR_URL


@pytest.fixture
def e2e_client(coordinator_url: str) -> WorkflowClient:
    """Create a workflow client for E2E tests."""
    return WorkflowClient(base_url=coordinator_url)


@pytest.fixture
def wait_for_workers(e2e_client: WorkflowClient, min_workers: int = 4) -> None:
    """Wait for minimum number of workers to be connected."""
    print(f"⏳ Waiting for at least {min_workers} workers...")

    start_time = time.time()
    while time.time() - start_time < 30:
        workers = e2e_client.get_workers()
        if len(workers) >= min_workers:
            print(f"✓ {len(workers)} workers connected")
            return
        time.sleep(1)

    raise TimeoutError(
        f"Expected at least {min_workers} workers, but only got {len(workers)}"
    )


@pytest.fixture
def workflow_waiter():
    """Factory fixture for waiting on workflow completion."""

    def _wait_for_workflow(
        client: WorkflowClient,
        workflow_id: str,
        timeout: int = 30,
        expected_status: WorkflowStatus = WorkflowStatus.COMPLETED
    ) -> Dict[str, Any]:
        """Wait for workflow to reach expected status.
        
        Args:
            client: WorkflowClient instance
            workflow_id: ID of the workflow to monitor
            timeout: Maximum time to wait in seconds
            expected_status: Expected final status
            
        Returns:
            Final workflow data as dictionary
            
        Raises:
            TimeoutError: If workflow doesn't reach expected status in time
        """
        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            workflow = client.get_workflow(workflow_id)

            if workflow.status != last_status:
                print(f"  Workflow {workflow_id}: {workflow.status}")
                last_status = workflow.status

            # Check if we've reached a terminal state
            if workflow.status in [
                    WorkflowStatus.COMPLETED, WorkflowStatus.FAILED,
                    WorkflowStatus.CANCELLED
            ]:
                if workflow.status == expected_status:
                    return workflow.model_dump()
                else:
                    raise AssertionError(
                        f"Workflow ended with status {workflow.status}, "
                        f"expected {expected_status}")

            time.sleep(0.5)

        raise TimeoutError(
            f"Workflow {workflow_id} did not reach {expected_status} within {timeout} seconds. "
            f"Last status: {last_status}")

    return _wait_for_workflow


@pytest.fixture
def workflow_definitions_path() -> Path:
    """Get the path to workflow definitions directory."""
    return Path(
        __file__).parent.parent.parent / "examples" / "workflow_definitions"


@pytest.fixture
def get_container_logs():
    """Factory fixture for getting container logs."""

    def _get_logs(service_name: str, tail: int = 50) -> str:
        """Get logs from a docker-compose service.
        
        Args:
            service_name: Name of the service (e.g., 'coordinator-e2e')
            tail: Number of lines to retrieve
            
        Returns:
            Log output as string
        """
        result = subprocess.run([
            "docker-compose", "-f",
            str(E2E_COMPOSE_FILE), "logs", "--tail",
            str(tail), service_name
        ],
                                capture_output=True,
                                text=True,
                                cwd=E2E_COMPOSE_FILE.parent)
        return result.stdout

    return _get_logs


@pytest.fixture
def stop_worker():
    """Factory fixture for stopping a worker container."""

    def _stop(worker_id: str) -> None:
        """Stop a worker container.
        
        Args:
            worker_id: Worker service name (e.g., 'worker-e2e-1')
        """
        subprocess.run(
            ["docker-compose", "-f",
             str(E2E_COMPOSE_FILE), "stop", worker_id],
            check=True,
            cwd=E2E_COMPOSE_FILE.parent)
        print(f"🛑 Stopped {worker_id}")

    return _stop


@pytest.fixture
def start_worker():
    """Factory fixture for starting a worker container."""

    def _start(worker_id: str) -> None:
        """Start a worker container.
        
        Args:
            worker_id: Worker service name (e.g., 'worker-e2e-1')
        """
        subprocess.run([
            "docker-compose", "-f",
            str(E2E_COMPOSE_FILE), "start", worker_id
        ],
                       check=True,
                       cwd=E2E_COMPOSE_FILE.parent)
        print(f"🟢 Started {worker_id}")
        time.sleep(2)  # Give it time to connect

    return _start
