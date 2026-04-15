# CIEM-Factory Canonical and Tool Schemas

## 1. Purpose

This document defines deterministic, implementation-ready schemas for:

- Job metadata and lifecycle payloads
- Canonical permission graph
- MCP tool input/output contracts
- Policy synthesis, validation, diff, and export bundle payloads

All examples are JSON. The implementation should use strict validation (`additionalProperties: false`) for all request bodies and core internal persisted entities.

---

## 2. Common Conventions

### 2.1 IDs and timestamps

- IDs are opaque strings using prefixes: `job-`, `art-`, `doc-`, `node-`, `edge-`, `run-`.
- Timestamps are RFC 3339 UTC (example: `2026-04-15T10:42:19Z`).
- `tenant_id` and `project_id` are mandatory for all persisted top-level entities.

### 2.2 Enumerations

- `provider`: `aws | azure | gcp | oci`
- `mode`: `design_time | runtime_rightsizing`
- `decision`: `included | excluded | conditional | unresolved`
- `severity`: `low | medium | high | critical`
- `status` (job): defined in `job-lifecycle-and-error-contract.md`

### 2.3 Base object pattern

All top-level entities should include:

```json
{
  "id": "opaque-id",
  "tenant_id": "tenant-123",
  "project_id": "proj-123",
  "created_at": "2026-04-15T10:42:19Z",
  "updated_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 3. Core Job Schemas

### 3.1 Job record

```json
{
  "id": "job-001",
  "tenant_id": "tenant-123",
  "project_id": "proj-123",
  "name": "payments-api-rightsizing",
  "mode": "design_time",
  "target_providers": ["aws"],
  "status": "created",
  "status_reason": null,
  "created_by": "user-456",
  "artifact_ids": ["art-001"],
  "policy_document_ids": ["doc-001"],
  "analysis_summary": {
    "providers_completed": [],
    "providers_failed": [],
    "has_partial_results": false
  },
  "created_at": "2026-04-15T10:42:19Z",
  "updated_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

### 3.2 Artifact record

```json
{
  "id": "art-001",
  "tenant_id": "tenant-123",
  "project_id": "proj-123",
  "job_id": "job-001",
  "artifact_type": "terraform",
  "source_ref": "./examples/payments/main.tf",
  "sha256": "hexstring",
  "size_bytes": 12903,
  "parser_status": "pending",
  "parser_errors": [],
  "created_at": "2026-04-15T10:42:19Z",
  "updated_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

### 3.3 Policy document record

```json
{
  "id": "doc-001",
  "tenant_id": "tenant-123",
  "project_id": "proj-123",
  "job_id": "job-001",
  "title": "Cloud Workload Least Privilege Standard",
  "scope": "global",
  "provider": "all",
  "environment": "prod",
  "priority": 100,
  "version": "2026.04",
  "effective_date": "2026-04-01",
  "expires_at": null,
  "content_type": "markdown",
  "source_ref": "object://policy-docs/doc-001",
  "extraction_status": "completed",
  "created_at": "2026-04-15T10:42:19Z",
  "updated_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 4. Canonical Permission Graph Schema

### 4.1 Graph envelope

```json
{
  "id": "graph-job-001",
  "tenant_id": "tenant-123",
  "project_id": "proj-123",
  "job_id": "job-001",
  "nodes": [],
  "edges": [],
  "build_metadata": {
    "artifact_ids": ["art-001"],
    "document_ids": ["doc-001"],
    "builder_version": "1.0.0"
  },
  "created_at": "2026-04-15T10:42:19Z",
  "updated_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

### 4.2 Node schema

```json
{
  "id": "node-123",
  "type": "principal",
  "provider": "aws",
  "attributes": {
    "name": "payments-runtime-role",
    "identity_type": "runtime_role"
  },
  "trace": {
    "artifact_id": "art-001",
    "source_path": "module.payments.aws_iam_role.runtime",
    "line_range": "12-37"
  }
}
```

Allowed `type` values:

- `principal`
- `resource`
- `action`
- `scope`
- `constraint`
- `evidence`
- `risk_signal`
- `decision`

### 4.3 Edge schema

```json
{
  "id": "edge-456",
  "type": "requires",
  "from_node_id": "node-principal-1",
  "to_node_id": "node-action-7",
  "attributes": {
    "confidence": 0.94
  },
  "trace": {
    "rule_id": "aws.lambda.invoke.mapping.v1",
    "evidence_ref": null
  }
}
```

Allowed `type` values:

- `requires`
- `implies`
- `constrained_by`
- `supported_by_evidence`
- `contradicted_by_evidence`
- `introduces_risk`
- `resolved_as`

---

## 5. MCP Tool Input/Output Contracts

## 5.1 `create_job`

Request:

```json
{
  "name": "payments-api-rightsizing",
  "project_id": "proj-123",
  "target_providers": ["aws"],
  "mode": "design_time"
}
```

Response:

```json
{
  "job_id": "job-001",
  "status": "created"
}
```

### 5.2 `upload_artifact_reference`

Request:

```json
{
  "job_id": "job-001",
  "artifact_type": "terraform",
  "path": "./examples/payments/main.tf"
}
```

Response:

```json
{
  "artifact_id": "art-001",
  "status": "registered"
}
```

### 5.3 `register_policy_document`

Request:

```json
{
  "job_id": "job-001",
  "title": "Cloud Workload Least Privilege Standard",
  "scope": "global",
  "provider": "all",
  "priority": 100,
  "content_type": "markdown",
  "content": "No workload identity may modify IAM roles..."
}
```

Response:

```json
{
  "document_id": "doc-001",
  "status": "registered"
}
```

### 5.4 `build_permission_graph`

Request:

```json
{
  "job_id": "job-001"
}
```

Response:

```json
{
  "job_id": "job-001",
  "graph_id": "graph-job-001",
  "status": "graph_built",
  "node_count": 148,
  "edge_count": 291
}
```

### 5.5 `generate_candidate_policy`

Request:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "identity_types": ["deployment_role", "runtime_role"]
}
```

Response:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "status": "policy_generated",
  "candidate_policy_id": "run-aws-001"
}
```

### 5.6 `validate_candidate_policy`

Request:

```json
{
  "job_id": "job-001",
  "provider": "aws"
}
```

Response:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "status": "validated",
  "validation_id": "run-aws-val-001",
  "result": "pass",
  "findings": []
}
```

### 5.7 `compare_current_permissions`

Request:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "current_policy": {
    "Version": "2012-10-17",
    "Statement": []
  }
}
```

Response:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "status": "diff_generated",
  "excess_actions": [],
  "missing_actions": [],
  "risk_delta_score": -23.4
}
```

### 5.8 `explain_permission`

Request:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "permission": "iam:PassRole"
}
```

Response:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "permission": "iam:PassRole",
  "decision": "excluded",
  "reason": "No deterministic deployment dependency found; high escalation risk.",
  "trace_refs": ["node-77", "edge-202", "rule-aws-risk-11"]
}
```

### 5.9 `export_policy_bundle`

Request:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "format": "json"
}
```

Response:

```json
{
  "job_id": "job-001",
  "provider": "aws",
  "bundle_id": "bundle-001",
  "status": "exported",
  "object_ref": "object://bundles/job-001/aws/bundle-001.json",
  "sha256": "hexstring",
  "signature_ref": "object://bundles/job-001/aws/bundle-001.sig"
}
```

---

## 6. Policy Candidate Schema

```json
{
  "id": "run-aws-001",
  "job_id": "job-001",
  "provider": "aws",
  "identity_policies": [
    {
      "identity_type": "deployment_role",
      "policy_document": { "Version": "2012-10-17", "Statement": [] },
      "trust_policy": { "Version": "2012-10-17", "Statement": [] },
      "decision_entries": [
        {
          "permission": "iam:PassRole",
          "decision": "excluded",
          "severity": "critical",
          "risk_score": 9.8,
          "rationale": "Escalation path without deterministic requirement",
          "trace_refs": ["edge-202"]
        }
      ]
    }
  ],
  "unresolved_requirements": [],
  "created_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 7. Validation Result Schema

```json
{
  "id": "run-aws-val-001",
  "job_id": "job-001",
  "provider": "aws",
  "result": "pass",
  "confidence_score": 0.86,
  "checks": [
    {
      "check_id": "aws.static.no_wildcard_admin",
      "name": "No wildcard admin actions",
      "result": "pass",
      "severity": "high",
      "details": "No iam:* or *:* detected."
    }
  ],
  "simulations": [],
  "findings": [],
  "created_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 8. Diff Schema

```json
{
  "id": "diff-001",
  "job_id": "job-001",
  "provider": "aws",
  "excess_permissions": ["iam:CreateRole"],
  "missing_permissions": [],
  "changed_scopes": [
    {
      "permission": "s3:GetObject",
      "current_scope": "arn:aws:s3:::*/*",
      "recommended_scope": "arn:aws:s3:::payments-prod/*"
    }
  ],
  "risk_delta_score": -23.4,
  "created_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 9. Export Bundle Schema

```json
{
  "id": "bundle-001",
  "job_id": "job-001",
  "provider": "aws",
  "bundle_type": "least_privilege_recommendation",
  "contents": {
    "candidate_policy_ref": "object://runs/run-aws-001.json",
    "validation_ref": "object://runs/run-aws-val-001.json",
    "diff_ref": "object://runs/diff-001.json",
    "explanation_ref": "object://runs/explain-001.json"
  },
  "integrity": {
    "sha256": "hexstring",
    "signature_ref": "object://bundles/job-001/aws/bundle-001.sig"
  },
  "created_at": "2026-04-15T10:42:19Z",
  "schema_version": "1.0.0"
}
```

---

## 10. Minimum Required Validation Rules

The implementation must reject:

- Unknown enum values
- Missing tenant or project scope
- Cross-job references (artifact/document from another job)
- Provider mismatch between request and generated entities
- Unsupported identity type values

The implementation should emit machine-readable errors per `job-lifecycle-and-error-contract.md`.
