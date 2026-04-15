import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ciem-factory-mcp", version="0.1.0")


class CreateJobToolInput(BaseModel):
  name: str
  project_id: str
  target_providers: list[str]
  mode: str


class UploadArtifactToolInput(BaseModel):
  job_id: str
  artifact_type: str
  path: str
  content: str


class RegisterPolicyDocumentToolInput(BaseModel):
  job_id: str
  title: str
  scope: str
  provider: str
  priority: int
  content_type: str
  content: str


class BuildPermissionGraphToolInput(BaseModel):
  job_id: str


class GenerateCandidatePolicyToolInput(BaseModel):
  job_id: str
  provider: str
  identity_types: list[str]


class ValidateCandidatePolicyToolInput(BaseModel):
  job_id: str
  provider: str


class CompareCurrentPermissionsToolInput(BaseModel):
  job_id: str
  provider: str
  current_policy: dict


class ExplainPermissionToolInput(BaseModel):
  job_id: str
  provider: str
  permission: str


class ExportPolicyBundleToolInput(BaseModel):
  job_id: str
  provider: str
  format: str = "json"


def _api_base_url() -> str:
  return os.getenv("CIEM_API_BASE_URL", "http://api:8000").strip()


async def _proxy_json(method: str, path: str, payload: dict | None = None) -> dict:
  async with httpx.AsyncClient(timeout=20.0) as client:
    response = await client.request(method, f"{_api_base_url()}{path}", json=payload)
  if response.status_code >= 400:
    raise HTTPException(status_code=response.status_code, detail=response.json())
  return response.json()


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok", "service": "mcp-server"}


@app.get("/mcp/info")
def mcp_info() -> dict[str, object]:
  return {
    "server": "ciem-factory",
    "resources": [
      "ciem://catalog/providers",
      "ciem://catalog/risk-rules",
      "ciem://jobs/{job_id}/artifacts",
      "ciem://jobs/{job_id}/policy-documents",
      "ciem://jobs/{job_id}/graph"
    ],
    "tools": [
      "create_job",
      "upload_artifact_reference",
      "register_policy_document",
      "build_permission_graph",
      "generate_candidate_policy",
      "validate_candidate_policy",
      "compare_current_permissions",
      "explain_permission",
      "export_policy_bundle"
    ]
  }


@app.post("/mcp/tools/create_job")
async def tool_create_job(payload: CreateJobToolInput) -> dict:
  job = await _proxy_json("POST", "/v1/jobs", payload.model_dump())
  return {"job_id": job["id"], "status": job["status"]}


@app.post("/mcp/tools/upload_artifact_reference")
async def tool_upload_artifact_reference(payload: UploadArtifactToolInput) -> dict:
  artifact = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/artifacts",
    {
      "artifact_type": payload.artifact_type,
      "path": payload.path,
      "content": payload.content
    }
  )
  return {"artifact_id": artifact["id"], "status": "registered"}


@app.post("/mcp/tools/register_policy_document")
async def tool_register_policy_document(payload: RegisterPolicyDocumentToolInput) -> dict:
  doc = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/policy-documents",
    {
      "title": payload.title,
      "scope": payload.scope,
      "provider": payload.provider,
      "priority": payload.priority,
      "content_type": payload.content_type,
      "content": payload.content
    }
  )
  return {"document_id": doc["id"], "status": "registered"}


@app.post("/mcp/tools/build_permission_graph")
async def tool_build_permission_graph(payload: BuildPermissionGraphToolInput) -> dict:
  graph = await _proxy_json("POST", f"/v1/jobs/{payload.job_id}/build-permission-graph")
  return graph


@app.post("/mcp/tools/generate_candidate_policy")
async def tool_generate_candidate_policy(payload: GenerateCandidatePolicyToolInput) -> dict:
  generated = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/generate-candidate-policy",
    {
      "provider": payload.provider,
      "identity_types": payload.identity_types
    }
  )
  return {
    "job_id": generated["job_id"],
    "provider": generated["provider"],
    "status": generated["status"],
    "candidate_policy_id": generated["id"]
  }


@app.post("/mcp/tools/validate_candidate_policy")
async def tool_validate_candidate_policy(payload: ValidateCandidatePolicyToolInput) -> dict:
  validated = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/validate-candidate-policy",
    {"provider": payload.provider}
  )
  return {
    "job_id": validated["job_id"],
    "provider": validated["provider"],
    "status": validated["status"],
    "validation_id": validated["id"],
    "result": validated["validation"]["result"],
    "findings": validated["validation"]["findings"]
  }


@app.post("/mcp/tools/compare_current_permissions")
async def tool_compare_current_permissions(payload: CompareCurrentPermissionsToolInput) -> dict:
  diff = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/compare-current-permissions",
    {
      "provider": payload.provider,
      "current_policy": payload.current_policy
    }
  )
  return {
    "job_id": diff["job_id"],
    "provider": diff["provider"],
    "status": diff["status"],
    "excess_actions": diff["diff"]["excess_permissions"],
    "missing_actions": diff["diff"]["missing_permissions"],
    "risk_delta_score": diff["diff"]["risk_delta_score"]
  }


@app.post("/mcp/tools/explain_permission")
async def tool_explain_permission(payload: ExplainPermissionToolInput) -> dict:
  return await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/explain-permission",
    {
      "provider": payload.provider,
      "permission": payload.permission
    }
  )


@app.post("/mcp/tools/export_policy_bundle")
async def tool_export_policy_bundle(payload: ExportPolicyBundleToolInput) -> dict:
  exported = await _proxy_json(
    "POST",
    f"/v1/jobs/{payload.job_id}/export-policy-bundle",
    {
      "provider": payload.provider,
      "format": payload.format
    }
  )
  bundle = exported["bundle"]
  return {
    "job_id": exported["job_id"],
    "provider": exported["provider"],
    "bundle_id": bundle["id"],
    "status": exported["status"],
    "object_ref": f"object://bundles/{exported['job_id']}/{exported['provider']}/{bundle['id']}.json",
    "sha256": bundle["integrity"]["sha256"],
    "signature_ref": bundle["integrity"]["signature_ref"]
  }
