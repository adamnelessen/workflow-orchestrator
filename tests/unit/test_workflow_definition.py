"""Tests for workflow definition parser"""
import pytest
from datetime import datetime

from coordinator.utils.workflow_parser import (parse_yaml_workflow,
                                               workflow_to_yaml,
                                               WorkflowDefinitionError)
from shared.enums import JobType, JobStatus, WorkflowStatus


def test_parse_simple_workflow():
    """Test parsing a simple workflow"""
    yaml_content = """
workflow:
  name: "test-workflow"
  jobs:
    - id: "job-1"
      type: "validation"
      parameters:
        key: "value"
"""

    workflow = parse_yaml_workflow(yaml_content)

    assert workflow.name == "test-workflow"
    assert workflow.status == WorkflowStatus.PENDING
    assert len(workflow.jobs) == 1
    assert workflow.jobs[0].id == "job-1"
    assert workflow.jobs[0].type == JobType.VALIDATION
    assert workflow.jobs[0].parameters == {"key": "value"}
    assert workflow.jobs[0].status == JobStatus.PENDING


def test_parse_workflow_with_conditional_flow():
    """Test parsing workflow with on_success and on_failure"""
    yaml_content = """
workflow:
  name: "conditional-workflow"
  jobs:
    - id: "validate"
      type: "validation"
      parameters: {}
      on_success: "process"
      on_failure: "notify"
    
    - id: "process"
      type: "processing"
      parameters: {}
    
    - id: "notify"
      type: "integration"
      parameters: {}
"""

    workflow = parse_yaml_workflow(yaml_content)

    assert len(workflow.jobs) == 3
    assert workflow.jobs[0].on_success == "process"
    assert workflow.jobs[0].on_failure == "notify"


def test_parse_workflow_with_always_run():
    """Test parsing workflow with always_run flag"""
    yaml_content = """
workflow:
  name: "cleanup-workflow"
  jobs:
    - id: "main-job"
      type: "processing"
      parameters: {}
    
    - id: "cleanup"
      type: "cleanup"
      parameters: {}
      always_run: true
"""

    workflow = parse_yaml_workflow(yaml_content)

    assert workflow.jobs[0].always_run is False
    assert workflow.jobs[1].always_run is True


def test_parse_workflow_with_max_retries():
    """Test parsing workflow with custom max_retries"""
    yaml_content = """
workflow:
  name: "retry-workflow"
  jobs:
    - id: "job-1"
      type: "processing"
      parameters: {}
      max_retries: 5
"""

    workflow = parse_yaml_workflow(yaml_content)

    assert workflow.jobs[0].max_retries == 5


def test_parse_workflow_missing_name():
    """Test that missing workflow name raises error"""
    yaml_content = """
workflow:
  jobs:
    - id: "job-1"
      type: "processing"
      parameters: {}
"""

    with pytest.raises(WorkflowDefinitionError, match="must have a 'name'"):
        parse_yaml_workflow(yaml_content)


def test_parse_workflow_missing_job_id():
    """Test that missing job ID raises error"""
    yaml_content = """
workflow:
  name: "test"
  jobs:
    - type: "processing"
      parameters: {}
"""

    with pytest.raises(WorkflowDefinitionError, match="must have an 'id'"):
        parse_yaml_workflow(yaml_content)


def test_parse_workflow_invalid_job_type():
    """Test that invalid job type raises error"""
    yaml_content = """
workflow:
  name: "test"
  jobs:
    - id: "job-1"
      type: "invalid-type"
      parameters: {}
"""

    with pytest.raises(WorkflowDefinitionError, match="invalid type"):
        parse_yaml_workflow(yaml_content)


def test_parse_workflow_invalid_job_reference():
    """Test that invalid job reference raises error"""
    yaml_content = """
workflow:
  name: "test"
  jobs:
    - id: "job-1"
      type: "processing"
      parameters: {}
      on_success: "non-existent-job"
"""

    with pytest.raises(WorkflowDefinitionError, match="non-existent job"):
        parse_yaml_workflow(yaml_content)


def test_parse_workflow_duplicate_job_ids():
    """Test that duplicate job IDs raise error"""
    yaml_content = """
workflow:
  name: "test"
  jobs:
    - id: "job-1"
      type: "processing"
      parameters: {}
    
    - id: "job-1"
      type: "validation"
      parameters: {}
"""

    with pytest.raises(WorkflowDefinitionError, match="Duplicate job ID"):
        parse_yaml_workflow(yaml_content)


def test_parse_workflow_invalid_yaml():
    """Test that invalid YAML raises error"""
    yaml_content = """
workflow:
  name: "test"
  jobs: [
    - id: "job-1"
"""

    with pytest.raises(WorkflowDefinitionError, match="Invalid YAML"):
        parse_yaml_workflow(yaml_content)


def test_workflow_to_yaml():
    """Test converting workflow back to YAML"""
    yaml_content = """
workflow:
  name: "test-workflow"
  jobs:
    - id: "job-1"
      type: "validation"
      parameters:
        key: "value"
      on_success: "job-2"
      always_run: true
    
    - id: "job-2"
      type: "processing"
      parameters: {}
"""

    workflow = parse_yaml_workflow(yaml_content)
    yaml_output = workflow_to_yaml(workflow)

    # Parse the output to verify it's valid
    workflow2 = parse_yaml_workflow(yaml_output)

    assert workflow.name == workflow2.name
    assert len(workflow.jobs) == len(workflow2.jobs)
    assert workflow.jobs[0].id == workflow2.jobs[0].id
    assert workflow.jobs[0].on_success == workflow2.jobs[0].on_success
    assert workflow.jobs[0].always_run == workflow2.jobs[0].always_run


def test_parse_data_processing_pipeline():
    """Test parsing the example data processing pipeline"""
    yaml_content = """
workflow:
  name: "data-processing-pipeline"
  jobs:
    - id: "validate-input"
      type: "validation"
      parameters:
        schema: "user-data"
      on_success: "process-data"
      on_failure: "send-error-notification"
    
    - id: "process-data"
      type: "processing"
      parameters:
        operation: "transform"
      on_success: "save-results"
      on_failure: "cleanup-temp-files"
    
    - id: "save-results"
      type: "integration"
      parameters:
        endpoint: "data-store"
    
    - id: "send-error-notification"
      type: "integration"
      parameters:
        recipient: "admin@company.com"
    
    - id: "cleanup-temp-files"
      type: "cleanup"
      parameters:
        target: "temp-files"
      always_run: true
"""

    workflow = parse_yaml_workflow(yaml_content)

    assert workflow.name == "data-processing-pipeline"
    assert len(workflow.jobs) == 5

    # Verify job structure
    job_map = {job.id: job for job in workflow.jobs}

    assert job_map["validate-input"].on_success == "process-data"
    assert job_map["validate-input"].on_failure == "send-error-notification"
    assert job_map["process-data"].on_success == "save-results"
    assert job_map["process-data"].on_failure == "cleanup-temp-files"
    assert job_map["cleanup-temp-files"].always_run is True
