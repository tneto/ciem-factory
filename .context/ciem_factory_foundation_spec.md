# CIEM-Factory Foundation Specification Pack

## 1. Product Definition

**Project name:** ciem-factory  
**Project type:** Multi-cloud MCP server for CIEM-driven least-privilege rightsizing  
**Primary mission:** Enable an LLM, through MCP, to analyze deployment intent, cloud resource requirements, runtime evidence, and user-provided policy context in order to generate the minimum viable permissions required to deploy and operate cloud applications with the lowest practical attack surface and lateral movement potential.

CIEM-factory will support AWS, Azure, GCP, and OCI. It will ingest multiple deployment artifact types including Terraform, CloudFormation, ARM/Bicep, Kubernetes manifests that imply cloud permissions, pipeline definitions, and other structured automation templates. It will also allow users to attach internal policy documents, cloud standards, security baselines, exception records, and architecture rules as contextual inputs.

The platform is not intended to be a generic enterprise IAM cleanup product in its first phases. Its first focus is application identities, workload identities, service principals, deployment roles, automation roles, and operational identities associated with cloud-hosted applications.

---

## 2. Problem Statement

Modern cloud applications are commonly deployed with roles that are overly broad because teams do not know the exact permissions required, cloud permission models are complex, and deployment tools often encourage convenience over least privilege. This creates three major risks:

1. Excessive control-plane permissions that allow an application or deployment pipeline to create, alter, or destroy infrastructure outside its scope.
2. Excessive data-plane permissions that allow reading, modifying, exporting, or deleting data that the application does not need.
3. Escalation and lateral movement permissions such as pass-role, impersonation, role assignment, secret read, policy write, network attachment, snapshot export, function code update, and key decryption capabilities.

CIEM-factory exists to reduce those risks while preserving deployability and operability.

---

## 3. Product Goals

CIEM-factory must:

- Read and normalize infrastructure and deployment intent across cloud providers.
- Determine the minimum permissions required for deployment and runtime operation.
- Reduce permissions that enable lateral movement, privilege escalation, or cross-boundary access.
- Accept user-supplied policy documents as contextual governance inputs.
- Produce explainable, traceable permission recommendations.
- Validate generated permission sets using provider-native simulation, analysis, or deterministic rule checks where possible.
- Expose the entire workflow through MCP resources, tools, and prompts.

CIEM-factory should also:

- Compare current permissions to recommended permissions.
- Support gradual rightsizing using deployment evidence and runtime logs.
- Produce reusable outputs suitable for CI/CD pipelines.
- Maintain provider-specific fidelity while using a unified internal model.

---

## 4. Non-Goals for MVP

The MVP will not attempt to:

- Fully replace enterprise IAM platforms.
- Automatically remediate every permission assignment in a cloud estate.
- Support every possible niche deployment engine on day one.
- Independently enforce permissions directly in cloud providers without approval workflows.
- Solve human user access governance, joiner/mover/leaver workflows, or enterprise identity lifecycle management.

---

## 5. Core Use Cases

### 5.1 Design-time least-privilege generation
A user provides Terraform or other automation artifacts for an application. CIEM-factory parses the resources, infers deployment and runtime requirements, applies governance context, and outputs the minimum candidate permissions for the application identity and deployment identity.

### 5.2 Runtime rightsizing
A user provides the current cloud role or policy attached to a workload identity along with runtime evidence such as access logs, denied actions, or execution traces. CIEM-factory proposes a smaller policy that preserves actual usage while removing risky or unnecessary actions.

### 5.3 Governance-constrained policy generation
A user uploads internal security standards or policy documents. CIEM-factory incorporates them as context and constrains generated permissions accordingly, for example preventing write access outside tagged environments or disallowing role-assignment capabilities.

### 5.4 Drift and over-privilege comparison
A user asks the system to compare what is currently granted versus what is minimally required. CIEM-factory returns a permission delta, risk score, and recommended reduction plan.

### 5.5 Explainability and audit
A user requests why a permission is needed or why a risky permission was removed. CIEM-factory explains the dependency chain from deployment artifact to permission requirement and documents alternative safer patterns where relevant.

---

## 6. Functional Requirements

### 6.1 Input support
CIEM-factory shall accept:

- Terraform modules and plans
- AWS CloudFormation templates
- Azure ARM templates and Bicep-rendered JSON
- GCP deployment descriptors where applicable
- OCI-related automation descriptors where applicable
- Kubernetes manifests with cloud-service implications
- CI/CD pipeline YAML or JSON files
- JSON, YAML, and structured policy documents
- Plain-text, Markdown, PDF, and DOCX policy documents supplied by users

### 6.2 Policy-context ingestion
CIEM-factory shall allow users to upload and register policy documents as contextual governance sources. Each document should support metadata such as:

- Title
- Scope
- Provider
- Environment
- Business unit
- Sensitivity level
- Effective date
- Version
- Priority / precedence

The system shall support global documents and application-specific overrides.

### 6.3 Multi-cloud permission analysis
CIEM-factory shall analyze permission requirements for:

- AWS IAM policies, trust policies, and deployment identities
- Azure role definitions, role assignments, scopes, actions, and data actions
- GCP IAM roles, bindings, custom roles, and service-account impersonation paths
- OCI policy statements, compartments, tenancy scope, verbs, and conditions

### 6.4 Least-privilege synthesis
CIEM-factory shall produce provider-native outputs including:

- AWS IAM policy JSON and trust recommendations
- Azure custom role definitions and recommended assignment scopes
- GCP custom roles and IAM binding recommendations
- OCI policy statements and scope recommendations

### 6.5 Risk-aware permission minimization
The system shall score permissions not only by functional necessity but also by abuse potential. High-risk capabilities shall be heavily penalized unless directly required.

Risk categories include:

- Privilege escalation
- Role passing or service impersonation
- Role or policy modification
- Secret retrieval
- Key decryption
- Storage enumeration or broad data read
- Snapshot or image export
- Network reconfiguration
- Function code replacement
- Identity federation manipulation
- Cross-account, cross-subscription, or cross-compartment reach

### 6.6 Traceability
For every generated permission, the system shall preserve a trace to:

- Source artifact element
- Dependency rule or provider mapping
- Policy-context constraint
- Runtime evidence if used
- Final decision rationale

### 6.7 Validation
Where available, CIEM-factory shall validate generated policies through:

- Static rule validation
- Provider-specific simulation or troubleshooting workflows
- Dry-run compatibility checks
- Conflict detection against user governance documents

---

## 7. Quality Attributes

### 7.1 Security
CIEM-factory must be secure by design because it processes sensitive architecture, permission, and policy information.

It must support:

- Tenant isolation
- Strong authentication and authorization
- Encryption at rest and in transit
- Immutable audit trails for policy generation runs
- Signed output bundles
- Scoped credentials for cloud validation
- Optional offline or restricted-context operation mode

### 7.2 Explainability
Every recommendation must be understandable by platform engineers, architects, and security teams. The system must prefer explicit reasoning over opaque outputs.

### 7.3 Determinism where possible
The LLM should aid interpretation and explanation, but deterministic provider rules must remain the source of truth for final policy generation and validation.

### 7.4 Extensibility
Provider adapters, parsers, and risk rules must be modular so that new deployment formats and cloud services can be added without redesigning the platform.

### 7.5 Performance
The system should handle typical application artifact sets within interactive time for design-time review and within batch time for larger runtime-rightsizing jobs.

---

## 8. Architecture Overview

CIEM-factory should use a layered architecture.

### 8.1 Main layers

1. **MCP Interface Layer**  
   Exposes resources, tools, and prompts to the LLM.

2. **Ingestion Layer**  
   Parses infrastructure artifacts, deployment files, runtime evidence, and user policy documents.

3. **Normalization Layer**  
   Converts all inputs into a cloud-agnostic permission intent graph.

4. **Dependency and Risk Analysis Layer**  
   Expands implied permissions, detects escalation vectors, and assigns risk weights.

5. **Provider Adapter Layer**  
   Maps normalized intent into AWS, Azure, GCP, and OCI native permission constructs.

6. **Policy Synthesis and Validation Layer**  
   Generates least-privilege outputs and validates them.

7. **Storage and Audit Layer**  
   Stores policy context, rule catalogs, evidence bundles, and audit trails.

### 8.2 High-level flow

```text
Input artifacts + policy docs + optional runtime evidence
                     |
                     v
            Ingestion and parsing
                     |
                     v
       Normalized permission intent graph
                     |
         +-----------+-----------+
         |           |           |
         v           v           v
       Risk      Dependency   Governance
      scoring     expansion    filters
         |           |           |
         +-----------+-----------+
                     |
                     v
         Provider-specific policy synthesis
                     |
                     v
        Validation, diffing, and explanation
                     |
                     v
          Final policy bundle and audit record
```

---

## 9. Internal Canonical Model

A core design principle is the use of a **canonical permission intent model**.

### 9.1 Main entities

- **Principal**: deployment role, workload identity, service principal, service account, instance profile, managed identity
- **Resource**: cloud object, service instance, API surface, dataset, network object, key, secret, queue, function, etc.
- **Action**: control-plane or data-plane operation
- **Scope**: tenancy, account, subscription, project, folder, compartment, region, resource group, tag scope, resource path
- **Constraint**: policy-context limitation, environment boundary, tag requirement, naming rule, denial rule
- **Evidence**: deployment logs, activity logs, denied actions, successful action traces
- **Risk Signal**: escalation, impersonation, mutation, exfiltration, network pivot, privilege boundary bypass
- **Decision**: included, excluded, conditional, unresolved

### 9.2 Canonical graph example

The system should internally represent relationships such as:

- principal requires action on resource at scope
- action implies secondary action
- action conflicts with governance rule
- action introduces risk signal
- runtime evidence supports or contradicts action necessity

This internal graph becomes the foundation for provider synthesis.

---

## 10. MCP Server Design

CIEM-factory should expose three MCP surfaces.

### 10.1 Resources

Resources provide contextual data to the LLM.

Recommended resources:

- `ciem://catalog/providers`
- `ciem://catalog/risk-rules`
- `ciem://documents/policy/{id}`
- `ciem://artifacts/source/{id}`
- `ciem://graphs/permission-intent/{id}`
- `ciem://evidence/runtime/{id}`
- `ciem://analysis/recommendation/{id}`
- `ciem://analysis/diff/{id}`
- `ciem://analysis/audit/{id}`

### 10.2 Tools

Recommended MCP tools:

- `parse_artifact`
- `register_policy_document`
- `list_policy_documents`
- `build_permission_graph`
- `expand_dependencies`
- `score_permission_risk`
- `analyze_provider_requirements`
- `generate_least_privilege_policy`
- `compare_with_current_permissions`
- `validate_candidate_policy`
- `explain_permission_decision`
- `export_policy_bundle`

### 10.3 Prompts

Recommended prompt workflows:

- Rightsize this Terraform deployment
- Rightsize this runtime role
- Apply these governance documents to policy generation
- Compare current versus minimum permissions
- Explain why this risky action was removed
- Generate provider-native outputs for all target clouds

---

## 11. Provider Adapter Contract

Each provider adapter must implement a common contract.

### 11.1 Required adapter methods

- Load provider permission catalog
- Resolve artifact resource types to provider actions
- Expand implied provider dependencies
- Identify provider-specific escalation and lateral movement patterns
- Generate provider-native least-privilege outputs
- Validate generated outputs using static or provider-native mechanisms
- Produce explainability mappings

### 11.2 AWS adapter focus

Must handle:

- IAM policies
- Trust policies
- `iam:PassRole`
- Service-linked roles
- Resource-level constraints
- Condition keys
- Runtime evidence from deployment and access logs

### 11.3 Azure adapter focus

Must handle:

- Management group, subscription, resource group, and resource scopes
- Custom roles
- Actions and dataActions
- Managed identities
- Role assignment permissions
- Provider operation mapping

### 11.4 GCP adapter focus

Must handle:

- IAM custom roles
- Service accounts
- Service-account impersonation
- Project, folder, and organization scopes
- Binding recommendations
- Predefined versus custom role decomposition

### 11.5 OCI adapter focus

Must handle:

- Policy statements
- Tenancy and compartment inheritance
- Verb-to-operation expansion
- Conditions
- Dynamic groups
- Cross-compartment risks

---

## 12. Policy Document Context Engine

This is a strategic differentiator and should be treated as its own subsystem.

### 12.1 Objectives

- Allow users to upload policy documents in multiple formats.
- Convert human policy text into structured constraints where possible.
- Preserve original document references for explainability.
- Support precedence and conflict resolution.

### 12.2 Constraint types

The system should extract or manually register constraints such as:

- Deny actions or deny categories
- Approved scope boundaries
- Approved regions or compartments
- Tag-based restrictions
- Mandatory encryption or key-boundary rules
- No cross-environment access
- No identity-modification permissions for workloads
- No network reconfiguration outside approved shared services
- Exception rules with expiration dates

### 12.3 Enforcement model

The LLM may help interpret document meaning, but constraints used in synthesis should be represented as machine-readable rule objects. The original text remains attached for traceability and explanation.

---

## 13. Suggested Repository Structure

```text
ciem-factory/
├── README.md
├── docs/
│   ├── product-spec.md
│   ├── architecture-spec.md
│   ├── mcp-contract.md
│   ├── provider-adapters.md
│   ├── policy-context-engine.md
│   ├── threat-model.md
│   └── roadmap.md
├── server/
│   ├── mcp/
│   ├── api/
│   └── auth/
├── core/
│   ├── canonical-model/
│   ├── analyzer/
│   ├── synthesis/
│   ├── validation/
│   ├── explainability/
│   └── scoring/
├── providers/
│   ├── aws/
│   ├── azure/
│   ├── gcp/
│   └── oci/
├── parsers/
│   ├── terraform/
│   ├── cloudformation/
│   ├── arm/
│   ├── kubernetes/
│   ├── pipelines/
│   └── documents/
├── policies/
│   ├── catalog/
│   ├── extracted/
│   └── precedence/
├── schemas/
│   ├── mcp/
│   ├── canonical/
│   ├── policy-docs/
│   └── outputs/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   └── benchmarks/
├── examples/
│   ├── terraform/
│   ├── cloudformation/
│   ├── arm/
│   └── policy-documents/
└── tools/
    ├── catalog-build/
    └── fixtures/
```

---

## 14. Security Design Requirements for CIEM-Factory Itself

Because the platform will process sensitive cloud architecture and security data, it should include:

- mTLS between internal services
- JWT-authenticated APIs
- Signed request and response payloads where relevant
- Role-based administrative separation
- Immutable audit ledger for generation runs and approvals
- Encrypted storage for uploaded documents and evidence
- Strict redaction rules for secrets
- Optional customer-managed keys for stored context
- Policy-bundle signing for downstream verification

The server should never assume that policy documents are safe to expose broadly. Access to uploaded context must be scoped to the correct tenant, project, and job.

---

## 15. MVP Scope

The MVP should focus on one narrow but powerful workflow:

**Given a Terraform or CloudFormation application plus optional policy documents, generate and explain a least-privilege deployment role and runtime role for AWS first, then extend the same internal architecture to Azure, GCP, and OCI.**

### 15.1 MVP capabilities

- MCP server with core tools and resources
- Terraform and CloudFormation parsing
- User policy document upload and contextual application
- Canonical permission intent graph
- AWS adapter with least-privilege policy generation
- Risk-aware scoring of escalation and lateral movement actions
- Human-readable explanation and machine-readable output bundle
- Comparison against current AWS policy

### 15.2 Post-MVP expansion

- Azure adapter
- GCP adapter
- OCI adapter
- Additional artifact types such as ARM/Bicep and broader pipeline ingestion
- Runtime tuning using logs and denied actions
- Approval workflow and CI/CD integration

---

## 16. Delivery Roadmap

### Phase 1: Foundation

- Define canonical permission model
- Build MCP server scaffolding
- Implement artifact ingestion contracts
- Implement policy document registration and storage
- Create initial risk taxonomy

### Phase 2: AWS-first vertical slice

- Terraform parser
- CloudFormation parser
- AWS dependency catalog
- AWS synthesis engine
- Explanation engine
- Static validation

### Phase 3: Governance and audit

- Policy-context extraction
- Precedence engine
- Traceability bundle
- Audit logging and signed outputs

### Phase 4: Multi-cloud expansion

- Azure adapter
- GCP adapter
- OCI adapter
- Unified diff and comparison views

### Phase 5: Runtime rightsizing

- Activity log ingestion
- Denied-action learning loop
- Convergence workflows for policy reduction

---

## 17. Key Design Principles

1. **Least privilege is necessary but not sufficient.** The system must optimize for low blast radius and low lateral movement as well.
2. **LLM-guided does not mean LLM-decided.** Deterministic provider rules must govern final output.
3. **Context is strategic.** User-provided policy documents are part of the decision system, not just attached files.
4. **Traceability is mandatory.** Every included or excluded permission must be explainable.
5. **AWS-first, multi-cloud by architecture.** The platform should start with one fully working provider slice while keeping the internal model cloud-agnostic.

---

## 18. Recommended Next Deliverables

The next practical documents to create are:

1. A full **Architecture Specification** with service-by-service design.
2. A **Repository Specification** tailored for implementation.
3. An **MCP Contract Specification** with exact resource and tool schemas.
4. An **AWS Adapter Specification** for the first vertical slice.
5. A **Threat Model** for ciem-factory itself.

These should be written so development can begin immediately.

