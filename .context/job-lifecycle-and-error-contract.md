# CIEM-Factory Job Lifecycle and Error Contract

## 1. Purpose

This document defines:

- The authoritative job state machine
- Transition rules and failure semantics
- Error format and error code catalog
- Retry, timeout, and idempotency behavior
- Partial-result guarantees

Deterministic execution behavior is mandatory for all MCP and internal API workflows.

---

## 2. Job State Machine

## 2.1 Canonical statuses

Allowed job statuses:

1. `created`
2. `inputs_registered`
3. `parsing`
4. `graph_built`
5. `policy_generating`
6. `policy_generated`
7. `validating`
8. `validated`
9. `diffing`
10. `exporting`
11. `completed`
12. `completed_with_warnings`
13. `failed`
14. `cancelled`

### 2.2 Transition rules

Legal transitions only:

- `created -> inputs_registered | cancelled`
- `inputs_registered -> parsing | failed | cancelled`
- `parsing -> graph_built | failed | completed_with_warnings`
- `graph_built -> policy_generating | failed | cancelled`
- `policy_generating -> policy_generated | completed_with_warnings | failed`
- `policy_generated -> validating | diffing | exporting | completed_with_warnings`
- `validating -> validated | completed_with_warnings | failed`
- `validated -> diffing | exporting | completed_with_warnings`
- `diffing -> exporting | completed_with_warnings | failed`
- `exporting -> completed | completed_with_warnings | failed`
- Any non-terminal state -> `cancelled`

Terminal states:

- `completed`
- `completed_with_warnings`
- `failed`
- `cancelled`

No transitions are allowed from terminal states.

### 2.3 Provider run sub-status

For multi-provider jobs, maintain per-provider sub-status:

- `pending | running | succeeded | warning | failed | skipped`

Job-level status should be:

- `completed` when all targeted providers are `succeeded`
- `completed_with_warnings` when at least one provider is `warning` or `skipped`, and none are `failed`
- `failed` when any mandatory provider run is `failed` and no usable output remains

---

## 3. Partial Result Semantics

### 3.1 Principle

CIEM-factory must return useful, marked outputs whenever deterministic work has succeeded, even if later stages fail.

### 3.2 Required behavior

- If parsing succeeds and validation fails, export candidate policy with `validation_status: "not_validated"`.
- If one provider fails in multi-provider mode, successful provider outputs remain accessible.
- If diffing fails, bundle still exports policy and validation sections with `diff_status: "unavailable"`.
- All partial outputs must include `warning_codes`.

### 3.3 Warning contract

Warnings are non-fatal and must include:

```json
{
  "code": "WARN_VALIDATION_SKIPPED",
  "message": "Validation integration not configured for this provider.",
  "stage": "validating",
  "retryable": false
}
```

---

## 4. Standard Error Envelope

All tool and API errors must return:

```json
{
  "error": {
    "code": "ERR_GRAPH_BUILD_FAILED",
    "message": "Unable to build canonical graph from registered artifacts.",
    "stage": "parsing",
    "retryable": true,
    "http_status": 422,
    "details": {
      "job_id": "job-001",
      "artifact_id": "art-001",
      "parser": "terraform"
    },
    "trace_id": "trc-abc-123"
  }
}
```

Rules:

- `code` is stable and machine-parsable.
- `message` is safe for end-user display and must not leak secrets.
- `details` contains non-sensitive debugging metadata only.

---

## 5. Error Code Catalog

### 5.1 Input and auth errors

- `ERR_UNAUTHORIZED`
- `ERR_FORBIDDEN`
- `ERR_TENANT_SCOPE_MISMATCH`
- `ERR_PROJECT_SCOPE_MISMATCH`
- `ERR_INVALID_INPUT_SCHEMA`
- `ERR_INPUT_TOO_LARGE`
- `ERR_UNSUPPORTED_ARTIFACT_TYPE`
- `ERR_UNSUPPORTED_CONTENT_TYPE`

### 5.2 Artifact and parsing errors

- `ERR_ARTIFACT_NOT_FOUND`
- `ERR_ARTIFACT_HASH_MISMATCH`
- `ERR_PARSER_TIMEOUT`
- `ERR_PARSER_SANDBOX_VIOLATION`
- `ERR_PARSER_MALFORMED_INPUT`
- `ERR_GRAPH_BUILD_FAILED`

### 5.3 Governance and synthesis errors

- `ERR_CONSTRAINT_EXTRACTION_FAILED`
- `ERR_CONSTRAINT_CONFLICT_UNRESOLVED`
- `ERR_PROVIDER_CATALOG_MISSING`
- `ERR_PROVIDER_MAPPING_INCOMPLETE`
- `ERR_POLICY_SYNTHESIS_FAILED`
- `ERR_UNRESOLVED_CRITICAL_PERMISSION`

### 5.4 Validation and export errors

- `ERR_VALIDATION_NOT_CONFIGURED`
- `ERR_VALIDATION_FAILED`
- `ERR_DIFF_FAILED`
- `ERR_BUNDLE_SIGNING_FAILED`
- `ERR_BUNDLE_EXPORT_FAILED`

### 5.5 Platform errors

- `ERR_RATE_LIMITED`
- `ERR_DEPENDENCY_UNAVAILABLE`
- `ERR_INTERNAL`

---

## 6. Idempotency and Retries

### 6.1 Idempotency

Write operations must support `idempotency_key`.

- Same key + same payload: return previous result.
- Same key + different payload: return `ERR_INVALID_INPUT_SCHEMA` with conflict details.

### 6.2 Retry policy

Retryable errors include transient failures only:

- dependency unavailable
- temporary provider API error
- timeout without deterministic failure evidence

Default retry policy:

- max attempts: `3`
- backoff: `exponential`
- jitter: `true`
- base delay: `500ms`
- max delay: `10s`

Non-retryable:

- invalid schema
- scope mismatch
- unsupported artifact or provider
- deterministic rule conflict requiring user action

---

## 7. Timeouts and Cancellation

- Artifact parsing timeout per artifact: `60s` (MVP default)
- Graph build timeout per job: `120s`
- Policy synthesis timeout per provider: `90s`
- Validation timeout per provider: `120s`
- Export/sign timeout: `30s`

On timeout:

- stage status becomes warning or failed based on partial outputs
- timeout error code emitted
- job can be retried from last stable checkpoint

Cancellation:

- `cancelled` is best-effort for in-flight tasks
- cancellation request must include caller identity and reason
- all cancellation events are audit logged

---

## 8. Checkpointing and Resume

Required checkpoints:

- `inputs_registered`
- `graph_built`
- `policy_generated` (per provider)
- `validated` (per provider)
- `exported` bundle metadata

Resume behavior:

- Resume always starts from latest successful checkpoint.
- Re-running an already completed stage is allowed only with `force_recompute=true`.

---

## 9. Audit Event Contract

Every status transition must emit:

```json
{
  "event_id": "evt-001",
  "job_id": "job-001",
  "timestamp": "2026-04-15T10:42:19Z",
  "actor": "system",
  "from_status": "parsing",
  "to_status": "graph_built",
  "stage": "parsing",
  "result": "success",
  "warning_codes": [],
  "error_code": null,
  "trace_id": "trc-abc-123"
}
```

Events are immutable and append-only.

---

## 10. MCP Tool Behavior by Status

- Tools requiring graph (`generate_candidate_policy`) must reject jobs before `graph_built`.
- `validate_candidate_policy` must reject before `policy_generated`.
- `export_policy_bundle` should allow export after `policy_generated`, while marking validation/diff sections as unavailable if not run.
- `compare_current_permissions` requires `policy_generated`.

Rejected transitions must return `ERR_INVALID_INPUT_SCHEMA` or a dedicated stage error with current status metadata.

---

## 11. Implementation Defaults (MVP)

- Single active run per `(job_id, provider)` pair.
- Background task queue required for `parsing`, `policy_generating`, `validating`.
- Polling endpoint should return both job-level status and provider sub-status.
- UI/MCP clients should treat `completed_with_warnings` as usable output that still needs review.
