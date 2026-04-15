import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


DB_PATH = Path(tempfile.gettempdir()) / "ciem_factory_test_mvp.db"
os.environ["CIEM_DB_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["CIEM_MODE"] = "local"
os.environ["CIEM_AUTH_MODE"] = "local_token"
os.environ["CIEM_TENANCY_MODE"] = "single"
os.environ["CIEM_SIGNING_KEY_SOURCE"] = "dev-local-key"

if DB_PATH.exists():
  DB_PATH.unlink()

from app import app  # noqa: E402


client = TestClient(app)


def _create_ready_job() -> str:
  job_response = client.post(
    "/v1/jobs",
    json={
      "name": "ready-job",
      "project_id": "proj-ready",
      "target_providers": ["aws"],
      "mode": "design_time"
    }
  )
  job_id = job_response.json()["id"]
  client.post(
    f"/v1/jobs/{job_id}/artifacts",
    json={
      "artifact_type": "terraform",
      "path": "./examples/terraform/lambda-s3.tf",
      "content": 'resource "aws_lambda_function" "fn" {}\nresource "aws_s3_bucket" "bucket" {}'
    }
  )
  client.post(
    f"/v1/jobs/{job_id}/policy-documents",
    json={
      "title": "Least Privilege Standard",
      "scope": "global",
      "provider": "all",
      "priority": 100,
      "content_type": "markdown",
      "content": "Disallow unmanaged privilege escalation actions."
    }
  )
  client.post(f"/v1/jobs/{job_id}/build-permission-graph")
  client.post(
    f"/v1/jobs/{job_id}/generate-candidate-policy",
    json={
      "provider": "aws",
      "identity_types": ["deployment_role", "runtime_role"]
    }
  )
  client.post(
    f"/v1/jobs/{job_id}/validate-candidate-policy",
    json={"provider": "aws"}
  )
  return job_id


def test_health_endpoint() -> None:
  response = client.get("/health")
  assert response.status_code == 200
  assert response.json()["status"] == "ok"


def test_create_job_register_doc_and_build_graph() -> None:
  job_response = client.post(
    "/v1/jobs",
    json={
      "name": "payments-api-rightsizing",
      "project_id": "proj-123",
      "target_providers": ["aws"],
      "mode": "design_time"
    }
  )
  assert job_response.status_code == 200
  job = job_response.json()
  assert job["status"] == "created"
  job_id = job["id"]

  artifact_response = client.post(
    f"/v1/jobs/{job_id}/artifacts",
    json={
      "artifact_type": "terraform",
      "path": "./examples/payments/main.tf",
      "content": 'resource "aws_s3_bucket" "payments" {}'
    }
  )
  assert artifact_response.status_code == 200
  assert artifact_response.json()["job_id"] == job_id

  doc_response = client.post(
    f"/v1/jobs/{job_id}/policy-documents",
    json={
      "title": "Least Privilege Standard",
      "scope": "global",
      "provider": "all",
      "priority": 100,
      "content_type": "markdown",
      "content": "No workload identity may modify IAM roles."
    }
  )
  assert doc_response.status_code == 200
  assert doc_response.json()["job_id"] == job_id

  updated_job_response = client.get(f"/v1/jobs/{job_id}")
  assert updated_job_response.status_code == 200
  assert updated_job_response.json()["status"] == "inputs_registered"

  graph_response = client.post(f"/v1/jobs/{job_id}/build-permission-graph")
  assert graph_response.status_code == 200
  graph = graph_response.json()
  assert graph["status"] == "graph_built"
  assert graph["graph_id"] == f"graph-{job_id}"
  assert graph["node_count"] >= 4
  assert graph["edge_count"] >= 3

  graph_get_response = client.get(f"/v1/jobs/{job_id}/graph")
  assert graph_get_response.status_code == 200
  graph_payload = graph_get_response.json()["graph"]
  assert graph_payload["job_id"] == job_id
  assert len(graph_payload["nodes"]) == graph_get_response.json()["node_count"]


def test_full_aws_mvp_pipeline() -> None:
  job_response = client.post(
    "/v1/jobs",
    json={
      "name": "full-pipeline-job",
      "project_id": "proj-full",
      "target_providers": ["aws"],
      "mode": "design_time"
    }
  )
  assert job_response.status_code == 200
  job_id = job_response.json()["id"]

  artifact_response = client.post(
    f"/v1/jobs/{job_id}/artifacts",
    json={
      "artifact_type": "terraform",
      "path": "./examples/terraform/lambda-s3.tf",
      "content": 'resource "aws_lambda_function" "fn" {}\nresource "aws_s3_bucket" "bucket" {}'
    }
  )
  assert artifact_response.status_code == 200

  doc_response = client.post(
    f"/v1/jobs/{job_id}/policy-documents",
    json={
      "title": "Least Privilege Standard",
      "scope": "global",
      "provider": "all",
      "priority": 100,
      "content_type": "markdown",
      "content": "Disallow unmanaged privilege escalation actions."
    }
  )
  assert doc_response.status_code == 200

  graph_response = client.post(f"/v1/jobs/{job_id}/build-permission-graph")
  assert graph_response.status_code == 200
  assert graph_response.json()["status"] == "graph_built"

  generate_response = client.post(
    f"/v1/jobs/{job_id}/generate-candidate-policy",
    json={
      "provider": "aws",
      "identity_types": ["deployment_role", "runtime_role"]
    }
  )
  assert generate_response.status_code == 200
  assert generate_response.json()["status"] == "policy_generated"
  candidate_policy = generate_response.json()["candidate_policy"]
  assert candidate_policy["provider"] == "aws"

  validate_response = client.post(
    f"/v1/jobs/{job_id}/validate-candidate-policy",
    json={"provider": "aws"}
  )
  assert validate_response.status_code == 200
  assert validate_response.json()["validation"]["result"] in {"pass", "fail"}

  export_response = client.post(
    f"/v1/jobs/{job_id}/export-policy-bundle",
    json={"provider": "aws", "format": "json"}
  )
  assert export_response.status_code == 200
  assert export_response.json()["bundle"]["integrity"]["sha256"]

  audit_response = client.get(f"/v1/jobs/{job_id}/audit")
  assert audit_response.status_code == 200
  assert audit_response.json()["available_sections"]["bundle"] is True


def test_build_graph_rejects_invalid_state() -> None:
  job_response = client.post(
    "/v1/jobs",
    json={
      "name": "no-inputs-job",
      "project_id": "proj-xyz",
      "target_providers": ["aws"],
      "mode": "design_time"
    }
  )
  job_id = job_response.json()["id"]
  response = client.post(f"/v1/jobs/{job_id}/build-permission-graph")
  assert response.status_code == 422
  assert response.json()["detail"]["error"]["code"] == "ERR_GRAPH_BUILD_FAILED"


def test_get_job_not_found_uses_job_error_code() -> None:
  response = client.get("/v1/jobs/job-does-not-exist")
  assert response.status_code == 404
  assert response.json()["detail"]["error"]["code"] == "ERR_JOB_NOT_FOUND"


def test_validate_rejects_completed_with_warnings_terminal_state() -> None:
  job_id = _create_ready_job()
  diff_response = client.post(
    f"/v1/jobs/{job_id}/compare-current-permissions",
    json={
      "provider": "aws",
      "current_policy": {
        "Version": "2012-10-17",
        "Statement": [
          {"Effect": "Allow", "Action": ["iam:CreateRole"], "Resource": "*"}
        ]
      }
    }
  )
  assert diff_response.status_code == 200
  validate_response = client.post(
    f"/v1/jobs/{job_id}/validate-candidate-policy",
    json={"provider": "aws"}
  )
  assert validate_response.status_code == 409
  assert validate_response.json()["detail"]["error"]["code"] == "ERR_INVALID_INPUT_SCHEMA"


def test_compare_rejects_completed_with_warnings_terminal_state() -> None:
  job_id = _create_ready_job()
  first_diff = client.post(
    f"/v1/jobs/{job_id}/compare-current-permissions",
    json={
      "provider": "aws",
      "current_policy": {
        "Version": "2012-10-17",
        "Statement": [
          {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "*"}
        ]
      }
    }
  )
  assert first_diff.status_code == 200
  second_diff = client.post(
    f"/v1/jobs/{job_id}/compare-current-permissions",
    json={
      "provider": "aws",
      "current_policy": {
        "Version": "2012-10-17",
        "Statement": []
      }
    }
  )
  assert second_diff.status_code == 409
  assert second_diff.json()["detail"]["error"]["code"] == "ERR_INVALID_INPUT_SCHEMA"


def test_compare_transitions_validated_to_completed_with_warnings() -> None:
  job_id = _create_ready_job()
  before = client.get(f"/v1/jobs/{job_id}")
  assert before.status_code == 200
  assert before.json()["status"] == "validated"

  diff_response = client.post(
    f"/v1/jobs/{job_id}/compare-current-permissions",
    json={
      "provider": "aws",
      "current_policy": {
        "Version": "2012-10-17",
        "Statement": []
      }
    }
  )
  assert diff_response.status_code == 200

  after = client.get(f"/v1/jobs/{job_id}")
  assert after.status_code == 200
  assert after.json()["status"] == "completed_with_warnings"


def test_export_rejects_completed_with_warnings_terminal_state() -> None:
  job_id = _create_ready_job()
  client.post(
    f"/v1/jobs/{job_id}/compare-current-permissions",
    json={
      "provider": "aws",
      "current_policy": {
        "Version": "2012-10-17",
        "Statement": [
          {"Effect": "Allow", "Action": ["iam:CreateRole"], "Resource": "*"}
        ]
      }
    }
  )
  export_response = client.post(
    f"/v1/jobs/{job_id}/export-policy-bundle",
    json={"provider": "aws", "format": "json"}
  )
  assert export_response.status_code == 409
  assert export_response.json()["detail"]["error"]["code"] == "ERR_INVALID_INPUT_SCHEMA"
