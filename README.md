# ciem-factory

CIEM-factory is an MCP-driven least-privilege platform for cloud application identities.
It analyzes deployment intent and governance context to generate explainable, risk-aware
permission recommendations.

## What is scaffolded now

- `ui/`: React + Vite starter interface for concept demos
- `services/api/`: FastAPI API with persisted MVP workflow endpoints
- `services/mcp-server/`: FastAPI MCP placeholder endpoints
- `services/worker/`: placeholder background worker
- `docker-compose.yml`: shared stack with `local` and `hosted` profiles
- `.context/*.md`: architecture, schema, lifecycle, validation, UI, and deployment specs

## MVP API slice (implemented)

- `POST /v1/jobs` create job
- `GET /v1/jobs` list jobs
- `GET /v1/jobs/{job_id}` get job
- `POST /v1/jobs/{job_id}/artifacts` register artifact reference + content
- `GET /v1/jobs/{job_id}/artifacts` list artifacts
- `POST /v1/jobs/{job_id}/policy-documents` register policy document
- `GET /v1/jobs/{job_id}/policy-documents` list policy documents
- `POST /v1/jobs/{job_id}/build-permission-graph` deterministic graph build
- `GET /v1/jobs/{job_id}/graph` fetch canonical graph payload
- `POST /v1/jobs/{job_id}/generate-candidate-policy`
- `GET /v1/jobs/{job_id}/provider/{provider}/candidate-policy`
- `POST /v1/jobs/{job_id}/validate-candidate-policy`
- `GET /v1/jobs/{job_id}/provider/{provider}/validation`
- `POST /v1/jobs/{job_id}/compare-current-permissions`
- `GET /v1/jobs/{job_id}/diff?provider=aws`
- `POST /v1/jobs/{job_id}/explain-permission`
- `POST /v1/jobs/{job_id}/export-policy-bundle`
- `GET /v1/jobs/{job_id}/audit?provider=aws`

## MCP tool bridge slice (implemented)

- `POST /mcp/tools/create_job`
- `POST /mcp/tools/upload_artifact_reference`
- `POST /mcp/tools/register_policy_document`
- `POST /mcp/tools/build_permission_graph`
- `POST /mcp/tools/generate_candidate_policy`
- `POST /mcp/tools/validate_candidate_policy`
- `POST /mcp/tools/compare_current_permissions`
- `POST /mcp/tools/explain_permission`
- `POST /mcp/tools/export_policy_bundle`

## Run local private profile

```bash
copy .env.local .env
docker compose --profile local up --build
```

Open:

- UI: `http://localhost:8080`
- API: `http://localhost:8000/health`
- MCP server: `http://localhost:8001/health`
- MinIO console: `http://localhost:9001`

## Run API MVP tests

```bash
cd services/api
pip install -r requirements.txt
pytest -q
```

## Run hosted simulation profile

```bash
copy .env.hosted .env
docker compose --profile hosted up --build
```

Hosted mode enables startup guardrails in the API:

- requires `CIEM_AUTH_MODE != disabled`
- requires `CIEM_TENANCY_MODE=multi`
- requires `CIEM_SIGNING_KEY_SOURCE` to be set

## Key docs

- `.context/ui-and-portability-spec.md`
- `.context/deployment-profiles-spec.md`
- `.context/canonical-and-tool-schemas.md`
- `.context/job-lifecycle-and-error-contract.md`
- `.context/aws-validation-and-catalog-governance-spec.md`
