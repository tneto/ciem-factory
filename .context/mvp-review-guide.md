# CIEM-Factory MVP Review Guide

## 1. Goal

This guide helps you quickly review what has been implemented in the MVP and how to validate the full AWS-first demo flow.

---

## 2. What Changed

Key implementation files:

- `services/api/app.py`
- `services/api/test_mvp.py`
- `services/mcp-server/app.py`
- `services/mcp-server/test_mcp.py`
- `ui/src/App.jsx`
- `docker-compose.yml`
- `README.md`

Key specification files:

- `.context/canonical-and-tool-schemas.md`
- `.context/job-lifecycle-and-error-contract.md`
- `.context/aws-validation-and-catalog-governance-spec.md`
- `.context/ui-and-portability-spec.md`
- `.context/deployment-profiles-spec.md`

---

## 3. Inspect Changes

From repo root:

```powershell
git status
git diff
```

To inspect specific changes:

```powershell
git diff -- services/api/app.py
git diff -- services/mcp-server/app.py
git diff -- ui/src/App.jsx
```

---

## 4. Run the Stack (Local Profile)

From repo root:

```powershell
copy .env.local .env
docker compose --profile local up --build
```

Open:

- UI: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`
- MCP info: `http://localhost:8001/mcp/info`

---

## 5. MVP End-to-End Demo Flow

In the UI (`http://localhost:8080`), run these buttons in order:

1. Create Job
2. Register Artifact
3. Register Policy Doc
4. Build Graph
5. Generate Policy
6. Validate
7. Diff
8. Explain
9. Export Bundle

Expected outcome:

- Job reaches completed state (`completed` or `completed_with_warnings`)
- JSON output panel shows generated data for each step
- API endpoints return valid payloads in `/docs`

---

## 6. Run Tests

API tests:

```powershell
cd services/api
pytest -q
```

MCP tests:

```powershell
cd ../mcp-server
pytest -q
```

UI build test:

```powershell
cd ../../ui
npm run build
```

Expected outcome:

- API tests pass
- MCP tests pass
- UI build succeeds

---

## 7. Quick API Checks (Optional)

Use Swagger at `http://localhost:8000/docs` or run examples with PowerShell:

```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8001/mcp/info
```

---

## 8. Current MVP Scope Boundary

Included now:

- AWS-first deterministic flow from inputs to export bundle
- Persisted job/artifact/document/graph/provider-analysis data
- MCP tool bridge for core workflow
- Containerized local and hosted-style profiles

Not yet included:

- Real Terraform/CloudFormation deep parsers
- Full provider-native simulation integrations
- Production auth/tenant enforcement implementation details

---

## 9. Recommended Next Review Step

After validating this guide, decide whether to:

1. commit current MVP baseline, then
2. start parser depth (Terraform/CloudFormation), or
3. strengthen validation/simulation fidelity for AWS.
