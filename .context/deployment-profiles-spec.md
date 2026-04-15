# CIEM-Factory Deployment Profiles Specification

## 1. Profile Definitions

Two first-class deployment profiles are required:

- `local`: private, portable deployment for offline/internal use
- `hosted`: web-hosted MCP deployment for shared environments

Both profiles use the same code artifacts and API/MCP contracts.

---

## 2. Component Matrix

| Component | local profile | hosted profile |
|---|---|---|
| UI | enabled | enabled |
| API | enabled | enabled |
| MCP server | enabled | enabled |
| Worker | enabled | enabled |
| PostgreSQL | local container | managed DB or container |
| Object store | MinIO | S3-compatible |
| Reverse proxy | optional | required |

---

## 3. Configuration Overlays

### 3.1 Base overlay (`.env`)

Shared defaults:

- service ports
- schema versions
- job queue parameters

### 3.2 Local overlay (`.env.local`)

- `CIEM_MODE=local`
- `CIEM_AUTH_MODE=local_token` (or `disabled` for demo-only)
- `CIEM_TENANCY_MODE=single`
- local data persistence volumes enabled

### 3.3 Hosted overlay (`.env.hosted`)

- `CIEM_MODE=hosted`
- `CIEM_AUTH_MODE=oidc`
- `CIEM_TENANCY_MODE=multi`
- secure secrets source required
- startup checks must fail on insecure auth mode

---

## 4. Data Portability Rules

- Export bundles and audit records must be mode-agnostic.
- No hosted-only data shape differences are allowed.
- Backups from local mode must restore in hosted mode and vice versa.

---

## 5. Startup Guardrails

Hosted startup must fail if:

- auth is disabled
- tenancy mode is single
- signing key source is unset

Local startup should warn (not fail) for:

- disabled auth
- unsigned bundle export configuration

---

## 6. Operational Commands (MVP)

- Local: `docker compose --profile local up --build`
- Hosted simulation: `docker compose --profile hosted up --build`

Future:

- Helm install profile overlays for real hosted clusters
