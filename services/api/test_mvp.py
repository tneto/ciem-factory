import os
from pathlib import Path

from fastapi.testclient import TestClient


DB_PATH = Path(__file__).parent / "test_mvp.db"
os.environ["CIEM_DB_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["CIEM_MODE"] = "local"
os.environ["CIEM_AUTH_MODE"] = "local_token"
os.environ["CIEM_TENANCY_MODE"] = "single"
os.environ["CIEM_SIGNING_KEY_SOURCE"] = "dev-local-key"

if DB_PATH.exists():
  DB_PATH.unlink()

from app import app  # noqa: E402


client = TestClient(app)


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
  assert response.status_code == 409
  assert response.json()["detail"]["error"]["code"] == "ERR_INVALID_STATE_TRANSITION"
