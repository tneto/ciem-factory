from fastapi.testclient import TestClient

import app as mcp_app


client = TestClient(mcp_app.app)


def test_mcp_info_lists_core_tools() -> None:
  response = client.get("/mcp/info")
  assert response.status_code == 200
  data = response.json()
  assert "create_job" in data["tools"]
  assert "export_policy_bundle" in data["tools"]


def test_create_job_tool_proxy_shape(monkeypatch) -> None:
  async def fake_proxy_json(method: str, path: str, payload: dict | None = None) -> dict:
    assert method == "POST"
    assert path == "/v1/jobs"
    return {"id": "job-123", "status": "created"}

  monkeypatch.setattr(mcp_app, "_proxy_json", fake_proxy_json)
  response = client.post(
    "/mcp/tools/create_job",
    json={
      "name": "test-job",
      "project_id": "proj-1",
      "target_providers": ["aws"],
      "mode": "design_time"
    }
  )
  assert response.status_code == 200
  assert response.json() == {"job_id": "job-123", "status": "created"}


def test_export_bundle_tool_proxy_shape(monkeypatch) -> None:
  async def fake_proxy_json(method: str, path: str, payload: dict | None = None) -> dict:
    assert method == "POST"
    assert path == "/v1/jobs/job-1/export-policy-bundle"
    return {
      "job_id": "job-1",
      "provider": "aws",
      "status": "completed",
      "bundle": {
        "id": "bundle-1",
        "integrity": {"sha256": "abc123", "signature_ref": "object://bundle.sig"}
      }
    }

  monkeypatch.setattr(mcp_app, "_proxy_json", fake_proxy_json)
  response = client.post(
    "/mcp/tools/export_policy_bundle",
    json={"job_id": "job-1", "provider": "aws", "format": "json"}
  )
  assert response.status_code == 200
  data = response.json()
  assert data["bundle_id"] == "bundle-1"
  assert data["sha256"] == "abc123"
