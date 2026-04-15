# CIEM-Factory AWS Validation and Catalog Governance Specification

## 1. Purpose

This document defines deterministic governance for:

- AWS permission/action catalog sourcing and versioning
- Catalog quality controls and update lifecycle
- AWS validation execution model for MVP
- Validation confidence and pass/fail semantics
- Fallback behavior when data or integrations are incomplete

This spec is AWS-focused for MVP and should be reused as a template for other providers.

---

## 2. AWS Catalog Governance

### 2.1 Catalog scope

The AWS catalog must represent:

- Service namespaces (for example: `s3`, `iam`, `lambda`)
- IAM actions by service
- Resource type support for each action
- Action access level category (`Read`, `Write`, `List`, `Permissions management`, `Tagging`)
- Condition keys and resource constraint notes where available
- Known dependency and implied action mappings
- High-risk action flags and risk class assignments

### 2.2 Catalog data sources

Allowed source classes:

1. Official AWS authorization references and service docs
2. Curated internal dependency rules maintained in repo
3. Manually approved exception mappings with provenance records

Prohibited:

- Unverified AI-generated action mappings as direct catalog source
- Runtime-derived action guesses without deterministic review

### 2.3 Catalog artifact format

Each service catalog file should include:

```json
{
  "provider": "aws",
  "service": "lambda",
  "catalog_version": "2026.04.15",
  "source_refs": [
    "https://docs.aws.amazon.com/service-authorization/latest/reference/list_awslambda.html"
  ],
  "generated_at": "2026-04-15T10:42:19Z",
  "actions": [
    {
      "name": "lambda:UpdateFunctionCode",
      "access_level": "Write",
      "resource_support": ["function"],
      "condition_keys": [],
      "risk_class": "code_mutation",
      "high_risk": true
    }
  ],
  "dependencies": [
    {
      "action": "lambda:CreateFunction",
      "implies": ["iam:PassRole", "logs:CreateLogGroup"]
    }
  ],
  "schema_version": "1.0.0"
}
```

### 2.4 Versioning and release rules

- Catalog version is date-based: `YYYY.MM.DD`.
- Catalogs are published independently of application release when needed.
- Every catalog release must be signed and include changelog entries:
  - added actions
  - removed/deprecated actions
  - changed dependency mappings
  - changed risk classifications

### 2.5 Review and approval workflow

Required checks before catalog publish:

1. Schema validation passes
2. No unresolved source provenance gaps
3. Golden test suite unchanged or intentionally updated with approvals
4. Security review for newly high-impact actions (`iam:*`, `sts:*`, `kms:Decrypt`, etc.)
5. Two-person approval for dependency-rule changes affecting escalation-sensitive actions

### 2.6 Staleness policy

- Catalogs older than `45` days should emit warning `WARN_CATALOG_STALE`.
- Catalogs older than `90` days must block `validated` status and downgrade to `completed_with_warnings` unless override is approved.
- Override requires explicit `allow_stale_catalog=true` and must be audit logged.

---

## 3. AWS Validation Execution Model

## 3.1 Validation objective

Validation confirms that generated policies are:

- syntactically valid
- aligned with deterministic dependency mappings
- minimally scoped where resolvable
- not introducing prohibited high-risk excess
- operationally plausible for declared workload intent

Validation does not guarantee absolute runtime success for unknown dynamic behavior.

### 3.2 Validation phases (MVP)

Phase 1: Static policy sanity checks

- JSON schema correctness
- statement structure validation
- deny known dangerous wildcard patterns (`*:*`, `iam:*` unless explicitly justified)
- trust policy structural checks for deployment/runtime identity split

Phase 2: Deterministic rule conformance

- every included action must trace to a graph dependency or approved governance exception
- dependency closure must be complete for selected services
- prohibited governance constraints must not be violated

Phase 3: Scope quality checks

- detect wildcard resource usage where narrower ARNs are derivable
- detect missing condition key opportunities for known sensitive actions
- verify separation of deployment and runtime permissions

Phase 4: Optional AWS simulator integration

- if configured, run selected simulation checks against representative action/resource tuples
- capture simulator outputs as advisory validation evidence

### 3.3 Validation result classes

- `pass`: no high/critical findings; medium findings below threshold
- `pass_with_warnings`: no critical findings, but unresolved medium/high warnings remain
- `fail`: one or more critical findings or deterministic conformance failure

### 3.4 Confidence scoring

`confidence_score` range: `0.0` to `1.0`.

Starting baseline: `1.0`, then reduce by weighted deductions:

- missing dependency evidence: `-0.20`
- wildcard scope unresolved: `-0.15`
- skipped simulator stage (when configured): `-0.10`
- stale catalog warning: `-0.15`
- unresolved high-risk action justification: `-0.25`

Clamp to `[0.0, 1.0]`.

`validated` status requires:

- `result` not equal `fail`
- `confidence_score >= 0.70`
- no `critical` findings

---

## 4. Validation Findings Schema

```json
{
  "finding_id": "fnd-001",
  "severity": "high",
  "code": "VAL_WILDCARD_SCOPE",
  "message": "Action s3:GetObject uses wildcard resource where narrowed ARN is derivable.",
  "action": "s3:GetObject",
  "recommended_fix": "Restrict to arn:aws:s3:::payments-prod/*",
  "trace_refs": ["node-52", "edge-121"],
  "blocking": false
}
```

Blocking finding codes (MVP):

- `VAL_POLICY_SYNTAX_INVALID`
- `VAL_CONFORMANCE_MISSING_TRACE`
- `VAL_CRITICAL_ESCALATION_UNJUSTIFIED`
- `VAL_TRUST_POLICY_INVALID`

---

## 5. Fallback and Degradation Rules

### 5.1 Simulator unavailable

If AWS simulator integration is unavailable:

- continue static + conformance checks
- emit `WARN_SIMULATOR_UNAVAILABLE`
- cap `confidence_score` at `0.85`
- allow `pass_with_warnings` but not strict `pass`

### 5.2 Incomplete catalog mapping

If required service/action mapping is missing:

- mark action as `unresolved`
- emit `ERR_PROVIDER_MAPPING_INCOMPLETE` if unresolved action is critical to deployment flow
- otherwise continue with `completed_with_warnings`

### 5.3 Missing runtime context

If runtime evidence is absent in design-time mode:

- no failure
- emit informational warning `WARN_RUNTIME_EVIDENCE_ABSENT`
- do not reduce confidence

---

## 6. Governance of High-Risk Actions

High-risk actions must include explicit justification records:

```json
{
  "action": "iam:PassRole",
  "risk_class": "privilege_escalation",
  "justification_required": true,
  "justification_source": "deterministic_dependency",
  "justification_ref": "rule-aws-deploy-passrole-02",
  "approved_exception_id": null
}
```

Rules:

- No high-risk action may be included without either deterministic dependency trace or approved exception.
- Governance exception must include owner, expiry, and ticket reference.
- Expired exceptions automatically invalidate validation pass.

---

## 7. Operational SLOs for MVP

- Static validation p95 per provider run: `< 10s`
- Conformance validation p95: `< 20s`
- End-to-end validation p95 without simulator: `< 30s`
- End-to-end validation p95 with simulator: `< 60s`

If SLO budget is exceeded:

- emit `WARN_VALIDATION_SLOW`
- keep results if correctness checks completed

---

## 8. Audit Requirements

Each validation run must record:

- `job_id`, `provider`, `catalog_version`
- validation engine version
- enabled phases and skipped phases
- findings list and severity counts
- confidence score calculation inputs
- final result class
- caller identity and timestamp

All validation records are immutable and linked to export bundle hash.

---

## 9. MVP Implementation Checklist

1. Define and enforce catalog schema.
2. Build catalog ingestion + signature verification.
3. Implement static validation rules and blocking codes.
4. Implement deterministic conformance checker against canonical graph traces.
5. Implement confidence scoring and result-class derivation.
6. Add simulator integration as optional module and degrade gracefully if absent.
7. Add golden tests for high-risk action handling and scope narrowing.
8. Add audit event emission for each phase and final result.

This checklist is the minimum bar before claiming production-ready AWS validation.
