# CIEM-Factory UI and Portability Specification

## 1. Purpose

This document adds two mandatory product capabilities:

- A user-facing web UI for demonstration and daily operation
- Portable deployment modes for hosted and private/local MCP usage

The same codebase must support both modes through configuration, not forks.

---

## 2. UI Scope for MVP

## 2.1 Core UI goals

- Make CIEM-factory understandable to non-specialists in live demos
- Show clear end-to-end flow from artifact upload to explainable policy output
- Provide visual evidence of risk reduction and least-privilege outcomes

### 2.2 MVP screens

1. Dashboard
   - Recent jobs
   - Status and provider badges
   - Validation outcome summary
2. New Analysis Job
   - Job metadata
   - Provider selection
   - Mode selection (`design_time` or `runtime_rightsizing`)
3. Artifact Upload
   - Add Terraform/CloudFormation artifacts
   - Show parse status and fingerprint
4. Governance Document Upload
   - Upload policy document
   - Set scope, priority, provider, effective dates
5. Analysis Result
   - Candidate deployment/runtime policies
   - Risk summary and excess-permission diff
   - Validation findings
6. Explainability View
   - Why included/excluded/conditional
   - Trace from source artifact to final decision

### 2.3 UI non-goals for MVP

- Full policy editing IDE
- Custom workflow builder
- Multi-organization administrative console

---

## 3. UI Technical Direction

- Frontend framework: React + Vite
- API pattern: Job-oriented REST calls to FastAPI
- Real-time status: polling in MVP; websocket optional later
- Auth handling:
  - Hosted mode: OIDC login
  - Local mode: local static token or disabled auth for offline sandbox mode

All business decisions remain backend-deterministic. UI is orchestration and visualization only.

---

## 4. Portable Deployment Model

## 4.1 Deployment modes

### Hosted mode

- Multi-tenant
- Public/private web endpoint
- OIDC auth required
- Managed PostgreSQL and object storage preferred
- MCP server exposed through ingress/gateway

### Local/private mode

- Single-tenant by default
- Runs on developer laptop or private server
- Optional offline mode
- Local PostgreSQL and object storage via containers or local paths
- MCP endpoint bound to localhost or private network

### 4.2 Shared runtime contract

Every mode must run the same components:

- `ui`
- `api`
- `mcp-server`
- `worker`
- `postgres`
- `object-store` (MinIO in local mode)

Differences are controlled by environment variables and deployment overlays.

---

## 5. Configuration Strategy

Required environment keys:

- `CIEM_MODE=local|hosted`
- `CIEM_AUTH_MODE=disabled|local_token|oidc`
- `CIEM_TENANCY_MODE=single|multi`
- `CIEM_API_BASE_URL`
- `CIEM_MCP_BASE_URL`
- `CIEM_DB_URL`
- `CIEM_OBJECT_STORE_ENDPOINT`
- `CIEM_OBJECT_STORE_BUCKET`
- `CIEM_SIGNING_KEY_SOURCE`

Rules:

- `local` mode defaults to `single` tenancy.
- `hosted` mode requires `multi` tenancy and auth not `disabled`.
- `disabled` auth is forbidden in hosted mode.

---

## 6. Container and Orchestration Requirements

### 6.1 Docker-first requirement

All deployable components must have Dockerfiles and runnable defaults.

### 6.2 Compose profiles

MVP must include:

- `docker compose --profile local up` for private local deployment
- `docker compose --profile hosted up` for hosted-like local simulation

### 6.3 Kubernetes readiness

Keep service boundaries and env-driven config compatible with future Helm/K8s manifests.

---

## 7. Security Expectations by Mode

### Local mode

- Local-only network binding by default
- Explicit warning banner in UI when auth is disabled
- Signed output bundles still required

### Hosted mode

- OIDC enforced
- TLS required at ingress
- Tenant and project isolation enforced
- Audit logging and rate limits enabled

---

## 8. MVP Acceptance Criteria

1. User can run local stack with one command and open a web UI.
2. User can create a job, upload artifact/document metadata, and trigger analysis flow.
3. User can view policy candidate, risk summary, validation status, and explanation traces.
4. Same API and MCP contracts work in both local and hosted profiles.
5. Hosted profile rejects startup if insecure auth settings are configured.
