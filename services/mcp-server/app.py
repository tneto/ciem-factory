from fastapi import FastAPI

app = FastAPI(title="ciem-factory-mcp", version="0.1.0")


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
      "ciem://jobs/{job_id}/graph"
    ],
    "tools": [
      "create_job",
      "register_policy_document",
      "build_permission_graph",
      "generate_candidate_policy",
      "validate_candidate_policy",
      "export_policy_bundle"
    ]
  }
