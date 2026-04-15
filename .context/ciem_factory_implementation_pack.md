# CIEM-Factory Implementation Pack

## 1. Architecture Specification

### 1.1 Architecture Objective

The ciem-factory architecture must allow an LLM, through MCP, to request deterministic multi-cloud permission analysis and policy synthesis for application deployment and runtime identities. The platform must separate contextual reasoning from policy truth so that generated outputs are explainable, testable, and safe to use in enterprise environments.

The architecture should be designed around one governing rule: **the LLM helps interpret intent and explain decisions, but deterministic engines, provider catalogs, risk rules, and policy constraints decide the final permission outputs.**

### 1.2 Logical Components

The platform should consist of the following logical services.

#### MCP Server
This is the front door. It exposes resources, tools, and prompt workflows to MCP clients. It performs request authentication, tenant scoping, job initiation, and output delivery. It should remain thin and delegate all heavy analysis to internal services.

#### Artifact Ingestion Service
This service receives IaC files, pipeline definitions, and structured automation artifacts. It validates format, fingerprints contents, extracts metadata, and hands files to the correct parser.

#### Document Context Service
This service handles user-supplied policy documents such as Markdown, PDF, DOCX, JSON, YAML, and plain text. It stores originals, extracts structured constraints where possible, versions each document, and builds a searchable governance-context object for later analysis.

#### Parser Layer
This layer contains format-specific parsers for Terraform, CloudFormation, ARM/Bicep-derived JSON, Kubernetes manifests, pipeline YAML, and additional future formats. Parsers convert source artifacts into a normalized internal representation.

#### Canonical Permission Graph Engine
This is the core platform engine. It builds a graph of principals, resources, actions, scopes, dependencies, constraints, evidence, and risk signals. Every downstream analysis step should operate on this graph rather than raw input files.

#### Dependency Expansion Engine
This engine enriches the graph with implied actions. For example, if a deployment creates a managed service that requires a logging sink, encryption key, and network binding, those implied needs must be represented here.

#### Risk Scoring Engine
This engine scores actions and relationships according to privilege-escalation, impersonation, exfiltration, mutation, and lateral-movement potential. It must also allow provider-specific risk rules and organization-specific weighting overrides.

#### Governance Constraint Engine
This engine applies user-supplied policy constraints and internal deterministic rules. It resolves document precedence, environment scope, provider scope, exception handling, and expiry rules.

#### Provider Adapters
Each adapter receives the canonical graph and produces provider-native permission outputs. The first release should include an AWS adapter, with Azure, GCP, and OCI following the same contract.

#### Policy Synthesis Engine
This engine takes provider mappings, risk scores, and governance outcomes and assembles final least-privilege output bundles. It must distinguish between required, optional, denied, and unresolved permissions.

#### Validation Engine
This engine validates outputs using provider-native simulators where available, static checks, and internal policy sanity checks. Validation results must be included in the output bundle.

#### Explainability Engine
This engine generates human-readable justifications, traces each permission to source requirements, and explains removals, denials, and unresolved ambiguities.

#### Storage and Audit Layer
This layer stores artifacts, generated graphs, extracted constraints, rules, job results, signed policy bundles, and immutable audit records.

### 1.3 Deployment Model

The preferred initial deployment model is a containerized microservice architecture on Kubernetes, aligned with your existing design preferences. However, for development speed, the early implementation can begin as a modular monorepo with a single deployable application process containing clearly separated packages. This allows a later split into services without rewriting business logic.

The recommended phases are:

- **Phase A:** Modular monolith with clear domain boundaries.
- **Phase B:** Split high-value subsystems into services, especially parsing, document processing, and validation.
- **Phase C:** Add asynchronous job orchestration for long-running multi-provider analysis.

### 1.4 Suggested Internal APIs

The internal APIs should be explicit and versioned.

- `POST /jobs/analyze`
- `POST /jobs/{id}/artifacts`
- `POST /jobs/{id}/policy-documents`
- `POST /jobs/{id}/build-graph`
- `POST /jobs/{id}/generate/{provider}`
- `POST /jobs/{id}/validate/{provider}`
- `GET /jobs/{id}/status`
- `GET /jobs/{id}/bundle`
- `GET /jobs/{id}/explanation`

All APIs must be JWT-authenticated and support tenant and project scoping.

### 1.5 Data Stores

The platform should use separate stores according to data type.

- **PostgreSQL** for metadata, job state, document records, extracted constraints, provider output metadata, and audit indices.
- **Object storage** for original uploaded files, output bundles, signed reports, and evidence packages.
- **Graph-capable internal model store** implemented initially in PostgreSQL JSONB or a dedicated graph representation inside the application layer. A graph database is optional later, not required for MVP.
- **Optional vector index** for semantic retrieval over policy documents and explanations, but only as a helper, never as the policy source of truth.

### 1.6 Recommended Technology Stack

Aligned with your broader platform preferences, the implementation stack should be:

- **Backend:** Python with FastAPI
- **MCP server integration:** Python MCP-compatible framework or direct MCP protocol implementation
- **Background tasks:** Temporal later, or Celery/RQ initially if needed
- **Storage:** PostgreSQL + S3-compatible object store
- **Auth:** Keycloak or Cognito depending deployment target
- **Secrets:** Vault or cloud-native equivalent
- **Policy rules:** OPA optional for governance evaluation later, but not necessary in MVP
- **Observability:** Prometheus, Loki, Tempo or OpenTelemetry-compatible stack
- **Containerization:** Docker
- **Deployment:** Local Kubernetes for development, EKS in production

### 1.7 End-to-End Analysis Flow

```text
User / MCP client
      |
      v
MCP Server
      |
      v
Job Orchestrator
      |
      +--> Artifact Ingestion --> Parsers --> Canonical Graph
      |
      +--> Policy Document Ingestion --> Constraint Extraction
      |
      +--> Dependency Expansion --> Risk Scoring --> Governance Filtering
      |
      +--> Provider Adapter --> Policy Synthesis --> Validation
      |
      +--> Explainability Engine --> Output Bundle + Audit Record
```

### 1.8 Failure Handling Philosophy

The system must not fail silently. It should produce structured partial results whenever possible. For example, if Terraform parsing succeeds but provider validation cannot run, the output should still include a candidate policy bundle clearly marked as unvalidated. This is especially important for MCP workflows where the LLM needs usable intermediate results.

---

## 2. Repository Specification

### 2.1 Repository Goals

The repository must support fast implementation, strong testing, modular evolution, and eventual separation into independently deployable components. It should keep provider logic, parsers, schemas, and core engines isolated.

### 2.2 Proposed Monorepo Layout

```text
ciem-factory/
├── README.md
├── LICENSE
├── .github/
│   ├── workflows/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── dependabot.yml
├── docs/
│   ├── foundation-spec.md
│   ├── architecture-spec.md
│   ├── repo-spec.md
│   ├── mcp-contract.md
│   ├── aws-adapter-spec.md
│   ├── threat-model.md
│   ├── decision-records/
│   └── diagrams/
├── apps/
│   ├── mcp-server/
│   ├── api/
│   └── worker/
├── packages/
│   ├── core-model/
│   ├── analyzer/
│   ├── synthesis/
│   ├── validation/
│   ├── explainability/
│   ├── governance/
│   ├── risk/
│   ├── provider-contract/
│   ├── provider-aws/
│   ├── provider-azure/
│   ├── provider-gcp/
│   ├── provider-oci/
│   ├── parser-terraform/
│   ├── parser-cloudformation/
│   ├── parser-arm/
│   ├── parser-kubernetes/
│   ├── parser-pipelines/
│   ├── parser-documents/
│   ├── schemas/
│   └── shared-utils/
├── catalogs/
│   ├── aws/
│   ├── azure/
│   ├── gcp/
│   ├── oci/
│   └── risk/
├── examples/
│   ├── terraform/
│   ├── cloudformation/
│   ├── policy-documents/
│   └── expected-outputs/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   ├── fixtures/
│   └── benchmarks/
├── deploy/
│   ├── docker/
│   ├── helm/
│   ├── terraform/
│   └── policies/
├── scripts/
│   ├── dev/
│   ├── catalog/
│   └── release/
└── Makefile
```

### 2.3 Repository Rules

Each package should have:

- A clearly defined contract
- Its own unit tests
- Type-checked models
- No direct reach-through into sibling package internals
- Minimal side effects

Provider packages must not embed canonical-model logic that should live in the shared core. Parser packages must not synthesize provider-native permissions directly. That separation is essential to keep the architecture clean.

### 2.4 Branching and Release Strategy

The simplest reliable model is:

- `main` as production-ready branch
- `develop` optional only if needed; otherwise trunk-based development is better
- short-lived feature branches
- semantic versioning for releases
- versioned provider catalogs independent from code releases where useful

### 2.5 CI/CD Requirements

Every pull request should run:

- Linting
- Type checks
- Unit tests
- Golden test comparison for known IaC inputs and expected policy outputs
- Contract tests for provider adapters
- Security scanning
- SBOM generation

Main branch merges should additionally run:

- Integration tests
- Build and sign container images
- Publish schemas and artifacts

### 2.6 Documentation Requirements

The repo should maintain ADRs for major architecture decisions, especially:

- why canonical graph over direct synthesis
- why AWS-first
- why deterministic rules outrank LLM reasoning
- why policy documents are extracted into structured constraints

---

## 3. MCP Contract Specification

### 3.1 MCP Design Goal

The MCP contract must allow a client LLM to discover context, invoke analysis functions, and follow reusable rightsizing workflows without exposing unsafe internal complexity.

### 3.2 Resource Model

Resources should be stable, typed, and scoped by tenant, project, and job.

#### Resource categories

**Catalog resources**
- `ciem://catalog/providers`
- `ciem://catalog/risk-rules`
- `ciem://catalog/services/{provider}`

**Input resources**
- `ciem://jobs/{job_id}/artifacts`
- `ciem://jobs/{job_id}/artifacts/{artifact_id}`
- `ciem://jobs/{job_id}/policy-documents`
- `ciem://jobs/{job_id}/policy-documents/{document_id}`

**Analysis resources**
- `ciem://jobs/{job_id}/graph`
- `ciem://jobs/{job_id}/risk-summary`
- `ciem://jobs/{job_id}/constraints`
- `ciem://jobs/{job_id}/provider/{provider}/candidate-policy`
- `ciem://jobs/{job_id}/provider/{provider}/validation`
- `ciem://jobs/{job_id}/diff`
- `ciem://jobs/{job_id}/audit`

### 3.3 Tool Model

Each tool should have deterministic input and output schemas.

#### Core tools

**`create_job`**
Creates a new analysis job.

Input:
```json
{
  "name": "payments-api-rightsizing",
  "project_id": "proj-123",
  "target_providers": ["aws"],
  "mode": "design_time"
}
```

Output:
```json
{
  "job_id": "job-001",
  "status": "created"
}
```

**`upload_artifact_reference`**
Registers an artifact already available to the server or passed through a supported client integration.

Input:
```json
{
  "job_id": "job-001",
  "artifact_type": "terraform",
  "path": "./examples/payments/main.tf"
}
```

**`register_policy_document`**
Registers a policy or governance document.

Input:
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

**`build_permission_graph`**
Parses artifacts and builds the canonical graph.

Input:
```json
{
  "job_id": "job-001"
}
```

**`generate_candidate_policy`**
Generates provider-native least-privilege outputs.

Input:
```json
{
  "job_id": "job-001",
  "provider": "aws",
  "identity_types": ["deployment_role", "runtime_role"]
}
```

**`validate_candidate_policy`**
Runs static and provider-specific validation.

Input:
```json
{
  "job_id": "job-001",
  "provider": "aws"
}
```

**`compare_current_permissions`**
Compares existing granted permissions against generated minimum permissions.

Input:
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

**`explain_permission`**
Explains why a permission was included, excluded, or flagged.

Input:
```json
{
  "job_id": "job-001",
  "provider": "aws",
  "permission": "iam:PassRole"
}
```

**`export_policy_bundle`**
Produces a final signed bundle.

Input:
```json
{
  "job_id": "job-001",
  "provider": "aws",
  "format": "json"
}
```

### 3.4 Prompt Workflows

The server should expose prompt templates such as:

- “Analyze this Terraform deployment and generate the minimum AWS deployment and runtime permissions.”
- “Apply these uploaded governance documents before generating permissions.”
- “Compare the current policy to the minimum candidate policy and explain the excess risk.”
- “Explain why this permission is necessary and whether a safer alternative exists.”

### 3.5 MCP Security Rules

The MCP interface must enforce:

- Tenant-aware job isolation
- Resource access controls
- Per-tool authorization
- Input size limits
- Safe output redaction when secrets or credentials appear in uploaded content

---

## 4. AWS Adapter Specification

### 4.1 AWS Adapter Mission

The AWS adapter is the first production-grade provider implementation. It must transform canonical permission requirements into least-privilege AWS IAM artifacts for deployment and runtime identities while reducing escalation and lateral movement potential.

### 4.2 Supported AWS Identity Types

The first version should support:

- CI/CD deployment role
- ECS task role
- Lambda execution role
- EKS workload role via IRSA or equivalent
- EC2 instance profile role
- Generic application runtime role

### 4.3 Supported Input Scenarios for MVP

- Terraform deploying AWS resources
- CloudFormation templates deploying AWS resources
- Optional current IAM policy for diffing
- Optional governance documents

### 4.4 AWS Canonical Mapping Responsibilities

The adapter must:

- map canonical actions to AWS IAM actions
- determine resource-level narrowing where possible
- apply condition keys where useful and safe
- separate trust-policy generation from permission-policy generation
- split deployment-role permissions from runtime-role permissions
- flag dangerous patterns such as wildcard resources or broad administrative APIs

### 4.5 High-Risk AWS Permissions

The adapter should explicitly detect and strongly penalize or flag:

- `iam:*`
- `iam:PassRole`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `iam:PutRolePolicy`
- `sts:AssumeRole` to non-approved roles
- `kms:Decrypt` on broad key scopes
- `secretsmanager:GetSecretValue` with wildcard resources
- `ssm:GetParameter*` across broad paths
- `ec2:CreateNetworkInterface` in shared-network patterns when unnecessary
- `lambda:UpdateFunctionCode`
- `cloudformation:*` when the identity should be runtime-only
- `s3:GetObject` and `s3:ListBucket` on broad or unrelated buckets

### 4.6 AWS Output Types

The adapter should generate:

- deployment role permission policy JSON
- runtime role permission policy JSON
- trust policy recommendations
- recommended resource scope narrowing
- list of denied or excluded risky permissions
- unresolved requirements requiring manual review

### 4.7 AWS Analysis Phases

#### Phase 1: Resource Discovery
Read parsed Terraform or CloudFormation objects and identify AWS services used.

#### Phase 2: Action Resolution
Map each intended operation to candidate IAM actions.

#### Phase 3: Dependency Expansion
Add required dependent actions such as describe, read, tagging, logging, and encryption-related actions.

#### Phase 4: Scope Narrowing
Restrict actions to specific ARNs, regions, paths, buckets, queues, secrets, or keys where possible.

#### Phase 5: Risk Reduction
Remove or replace overly broad actions, split identities, and recommend safer trust relationships.

#### Phase 6: Validation
Run static validation and simulation hooks where integrated.

### 4.8 AWS Explainability Requirements

For each generated permission, the adapter must provide:

- originating artifact element
- mapped AWS service and action
- reason for inclusion
- scope decision
- associated risks
- whether it is required for deployment, runtime, or both

### 4.9 AWS Golden Test Examples

The adapter should ship with known-good fixtures such as:

- Lambda + API Gateway + DynamoDB
- ECS service + ALB + CloudWatch Logs + Secrets Manager
- S3 static site + CloudFront + Route 53
- EKS deployment with IRSA-scoped S3 and SQS access
- RDS-backed application with narrowly scoped secret and KMS access

These tests should assert both required permissions and prohibited risky expansions.

---

## 5. Threat Model for CIEM-Factory

### 5.1 Threat Model Objective

CIEM-factory processes highly sensitive material including deployment intent, security policy documents, current permissions, and sometimes cloud validation credentials. The threat model must protect confidentiality, integrity, isolation, and trustworthiness of outputs.

### 5.2 Protected Assets

The main protected assets are:

- uploaded infrastructure artifacts
- uploaded policy and governance documents
- extracted constraints
- current IAM policies and bindings
- generated least-privilege policies
- provider validation credentials
- audit logs and signed output bundles
- tenant isolation boundaries

### 5.3 Trust Boundaries

The main trust boundaries are:

- MCP client to MCP server
- MCP server to internal analysis services
- internal services to storage
- internal services to cloud-provider validation endpoints
- tenant A to tenant B
- LLM reasoning layer to deterministic policy engines

### 5.4 Primary Threats

#### Cross-tenant data leakage
One tenant’s uploaded policy documents or generated outputs must never be visible to another tenant.

Mitigations:
- strict tenant scoping in every request
- row-level security or equivalent access enforcement
- object-storage prefix isolation
- signed access tokens with tenant claims

#### Prompt-context leakage into model interactions
Sensitive policy content could be overexposed if too much raw context is passed into model reasoning.

Mitigations:
- minimize context sent to model
- prefer extracted structured constraints over raw text
- redact secrets and credentials
- support restricted or offline reasoning modes

#### Malicious uploaded documents
A user may upload malformed or adversarial files designed to exploit parsers or poison context.

Mitigations:
- sandbox file parsing
- MIME and structure validation
- antivirus or file scanning where relevant
- content size and depth limits
- parser timeouts

#### Policy poisoning
A malicious or incorrect governance document could steer generated outputs toward unsafe permissions or deny critical actions.

Mitigations:
- precedence rules
- versioning
- document approval states
- explainable constraint traceability
- manual override workflow for high-impact conflicts

#### Output tampering
Generated policy bundles could be altered after generation.

Mitigations:
- sign policy bundles
- store immutable audit records
- hash outputs and inputs per job

#### Excessive validation privileges
Cloud validation credentials may themselves be overprivileged.

Mitigations:
- dedicated low-privilege validation identities
- provider-specific scoped roles
- short-lived credentials
- auditable credential usage

#### Supply-chain compromise
Dependencies, catalogs, or build pipelines may be tampered with.

Mitigations:
- signed builds
- SBOM generation
- dependency pinning and scanning
- image signing and provenance tracking

#### Unsafe LLM overreach
The LLM may suggest permissions unsupported by deterministic evidence.

Mitigations:
- deterministic policy compiler as source of truth
- no direct freeform output as final policy
- flag unsupported suggestions as advisory only

### 5.5 Security Controls Baseline

CIEM-factory should enforce:

- mTLS for service-to-service communication
- JWT-based authN/authZ
- encrypted storage with KMS-backed keys
- immutable audit trail
- signed bundles
- secret redaction in logs and explanations
- strict admin separation
- rate limiting and abuse controls

### 5.6 Logging and Audit Requirements

Every analysis job must record:

- who initiated it
- which artifacts and documents were used
- what constraints were extracted
- which provider adapters ran
- what outputs were generated
- whether validation succeeded or failed
- hashes of the final bundle

### 5.7 High-Level Threat Diagram

```text
User / Client
    |
    v
MCP Server  <---- auth / tenant boundary ---->  Identity Provider
    |
    v
Internal Services ----> Storage
    |
    +----> Cloud validation APIs
    |
    +----> LLM reasoning boundary
```

The most important design decision is that the LLM reasoning boundary is not trusted to define final permission truth.

---

## 6. Recommended Immediate Build Order

The implementation sequence should be:

First, create the canonical schemas and job model. Second, scaffold the MCP server and the internal job orchestration flow. Third, implement Terraform and CloudFormation parsers for AWS-focused fixtures. Fourth, build the AWS adapter and golden tests. Fifth, add policy document ingestion and structured constraint extraction. Sixth, add explainability and signed export bundles. Seventh, add validation hooks and diffing.

That order will get you to a credible AWS-first working platform quickly without blocking the multi-cloud architecture.

---

## 7. Suggested First Sprint Breakdown

### Sprint 1
- repo scaffolding
- core schema definitions
- create_job and register_policy_document tools
- basic artifact registration flow

### Sprint 2
- Terraform parser MVP
- canonical graph builder MVP
- initial AWS service/action catalog

### Sprint 3
- AWS deployment/runtime policy synthesis
- risk scoring MVP
- first golden test fixtures

### Sprint 4
- explanation engine
- policy diffing
- export bundle generation

### Sprint 5
- governance constraint extraction
- signed outputs
- validation hooks

---

## 8. Final Implementation Principle

Build ciem-factory so that each permission in the final output can be defended in a design review. If the platform cannot explain why a permission exists, why its scope is as wide as it is, and what risk it introduces, then that permission should not be considered production-ready.

