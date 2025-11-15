from client.workflow_client import WorkflowClient
import time


def create_data_processing_workflow() -> dict:
    """Create a data processing workflow with conditional paths."""
    return {
        "name":
        "data-processing-pipeline",
        "jobs": [{
            "id": "validate-input",
            "type": "validation",
            "parameters": {
                "schema": "user-data"
            },
            "on_success": "process-data",
            "on_failure": "send-error-notification"
        }, {
            "id": "process-data",
            "type": "processing",
            "parameters": {
                "operation": "transform",
                "duration": 3
            },
            "on_success": "save-results",
            "on_failure": "cleanup-temp-files"
        }, {
            "id": "save-results",
            "type": "integration",
            "parameters": {
                "endpoint": "data-store"
            }
        }, {
            "id": "send-error-notification",
            "type": "integration",
            "parameters": {
                "recipient": "admin@company.com"
            }
        }, {
            "id": "cleanup-temp-files",
            "type": "cleanup",
            "parameters": {
                "target": "temp-files"
            },
            "always_run": True
        }]
    }


def create_deployment_workflow() -> dict:
    """Create a deployment workflow."""
    return {
        "name":
        "deployment-pipeline",
        "jobs": [{
            "id": "build-code",
            "type": "processing",
            "parameters": {
                "operation": "build",
                "duration": 2
            },
            "on_success": "run-tests",
            "on_failure": "notify-build-failure"
        }, {
            "id": "run-tests",
            "type": "validation",
            "parameters": {
                "schema": "test-suite"
            },
            "on_success": "deploy-staging",
            "on_failure": "notify-test-failure"
        }, {
            "id": "deploy-staging",
            "type": "integration",
            "parameters": {
                "endpoint": "staging-server"
            },
            "on_success": "deploy-production",
            "on_failure": "rollback"
        }, {
            "id": "deploy-production",
            "type": "integration",
            "parameters": {
                "endpoint": "production-server"
            }
        }, {
            "id": "rollback",
            "type": "cleanup",
            "parameters": {
                "target": "deployment"
            }
        }, {
            "id": "notify-build-failure",
            "type": "integration",
            "parameters": {
                "recipient": "dev-team@company.com"
            }
        }, {
            "id": "notify-test-failure",
            "type": "integration",
            "parameters": {
                "recipient": "qa-team@company.com"
            }
        }]
    }


def main():
    """Main function to demonstrate the workflow system."""
    client = WorkflowClient()

    print("Adam's Workflow Orchestration System - Demo Client")
    print("=" * 50)

    # Check worker status
    print("\n1. Checking connected workers...")
    workers = client.get_workers()
    print(f"   Connected workers: {len(workers)}")
    for worker in workers:
        capabilities = ", ".join(worker.capabilities)
        print(f"   - {worker.id}: {capabilities}")

    # Submit data processing workflow
    # print("\n2. Submitting data processing workflow...")
    # workflow1 = create_data_processing_workflow()
    # workflow1_id = client.submit_workflow(workflow1)
    # print(f"   Workflow ID: {workflow1_id}")

    # # Submit deployment workflow
    # print("\n3. Submitting deployment workflow...")
    # workflow2 = create_deployment_workflow()
    # workflow2_id = client.submit_workflow(workflow2)
    # print(f"   Workflow ID: {workflow2_id}")

    # # Monitor workflows
    # print("\n4. Monitoring workflow execution...")

    # # Wait for both workflows
    # try:
    #     print(f"\n   Workflow 1 ({workflow1_id}):")
    #     status1 = client.wait_for_workflow(workflow1_id, timeout=30)
    #     print(f"   Status: {status1['status']}")
    #     print(
    #         f"   Completed jobs: {status1['completed_jobs']}/{status1['job_count']}"
    #     )

    #     # Show job details
    #     jobs1 = client.get_workflow_jobs(workflow1_id)
    #     for job in jobs1:
    #         print(f"     - {job['job_id']}: {job['status']}")

    #     print(f"\n   Workflow 2 ({workflow2_id}):")
    #     status2 = client.wait_for_workflow(workflow2_id, timeout=30)
    #     print(f"   Status: {status2['status']}")
    #     print(
    #         f"   Completed jobs: {status2['completed_jobs']}/{status2['job_count']}"
    #     )

    #     # Show job details
    #     jobs2 = client.get_workflow_jobs(workflow2_id)
    #     for job in jobs2:
    #         print(f"     - {job['job_id']}: {job['status']}")

    # except TimeoutError as e:
    #     print(f"   Error: {e}")
    # except Exception as e:
    #     print(f"   Error: {e}")

    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    main()
