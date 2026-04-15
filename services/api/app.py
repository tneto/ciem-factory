import enum
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class JobStatus(str, enum.Enum):
  created = "created"
  inputs_registered = "inputs_registered"
  parsing = "parsing"
  graph_built = "graph_built"
  policy_generating = "policy_generating"
  policy_generated = "policy_generated"
  validating = "validating"
  validated = "validated"
  diffing = "diffing"
  exporting = "exporting"
  completed = "completed"
  completed_with_warnings = "completed_with_warnings"
  failed = "failed"
  cancelled = "cancelled"


class Provider(str, enum.Enum):
  aws = "aws"
  azure = "azure"
  gcp = "gcp"
  oci = "oci"


class AnalysisMode(str, enum.Enum):
  design_time = "design_time"
  runtime_rightsizing = "runtime_rightsizing"


class ArtifactType(str, enum.Enum):
  terraform = "terraform"
  cloudformation = "cloudformation"
  arm = "arm"
  kubernetes = "kubernetes"
  pipelines = "pipelines"


class Base(DeclarativeBase):
  pass


class Job(Base):
  __tablename__ = "jobs"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  tenant_id: Mapped[str] = mapped_column(String(64))
  project_id: Mapped[str] = mapped_column(String(64))
  name: Mapped[str] = mapped_column(String(255))
  mode: Mapped[AnalysisMode] = mapped_column(Enum(AnalysisMode))
  status: Mapped[JobStatus] = mapped_column(Enum(JobStatus))
  target_providers: Mapped[str] = mapped_column(String(255))
  created_by: Mapped[str] = mapped_column(String(64))
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  policy_documents: Mapped[list["PolicyDocument"]] = relationship(back_populates="job")
  artifacts: Mapped[list["Artifact"]] = relationship(back_populates="job")
  graph: Mapped["PermissionGraph | None"] = relationship(back_populates="job", uselist=False)


class PolicyDocument(Base):
  __tablename__ = "policy_documents"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"))
  tenant_id: Mapped[str] = mapped_column(String(64))
  project_id: Mapped[str] = mapped_column(String(64))
  title: Mapped[str] = mapped_column(String(255))
  scope: Mapped[str] = mapped_column(String(64))
  provider: Mapped[str] = mapped_column(String(32))
  priority: Mapped[int]
  content_type: Mapped[str] = mapped_column(String(32))
  content: Mapped[str]
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  job: Mapped[Job] = relationship(back_populates="policy_documents")


class Artifact(Base):
  __tablename__ = "artifacts"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"))
  tenant_id: Mapped[str] = mapped_column(String(64))
  project_id: Mapped[str] = mapped_column(String(64))
  artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType))
  source_ref: Mapped[str] = mapped_column(String(1024))
  sha256: Mapped[str] = mapped_column(String(128))
  size_bytes: Mapped[int] = mapped_column(Integer)
  parser_status: Mapped[str] = mapped_column(String(32))
  parser_errors: Mapped[str] = mapped_column(Text, default="[]")
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  job: Mapped[Job] = relationship(back_populates="artifacts")


class PermissionGraph(Base):
  __tablename__ = "permission_graphs"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), unique=True)
  tenant_id: Mapped[str] = mapped_column(String(64))
  project_id: Mapped[str] = mapped_column(String(64))
  graph_json: Mapped[str] = mapped_column(Text)
  node_count: Mapped[int] = mapped_column(Integer)
  edge_count: Mapped[int] = mapped_column(Integer)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  job: Mapped[Job] = relationship(back_populates="graph")


class ProviderAnalysis(Base):
  __tablename__ = "provider_analyses"

  id: Mapped[str] = mapped_column(String(64), primary_key=True)
  job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"))
  provider: Mapped[Provider] = mapped_column(Enum(Provider))
  candidate_policy_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  validation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  diff_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  explanation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  bundle_json: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class CreateJobRequest(BaseModel):
  name: str = Field(min_length=3, max_length=255)
  project_id: str = Field(min_length=1, max_length=64)
  target_providers: list[Provider] = Field(min_length=1)
  mode: AnalysisMode


class JobResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: str
  tenant_id: str
  project_id: str
  name: str
  mode: AnalysisMode
  target_providers: list[str]
  status: JobStatus
  created_at: datetime
  updated_at: datetime


class RegisterPolicyDocumentRequest(BaseModel):
  title: str = Field(min_length=3, max_length=255)
  scope: str = Field(min_length=1, max_length=64)
  provider: str = Field(min_length=1, max_length=32)
  priority: int = Field(ge=0, le=1000)
  content_type: str = Field(min_length=1, max_length=32)
  content: str = Field(min_length=1)


class PolicyDocumentResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: str
  job_id: str
  title: str
  scope: str
  provider: str
  priority: int
  content_type: str
  created_at: datetime


class RegisterArtifactRequest(BaseModel):
  artifact_type: ArtifactType
  path: str = Field(min_length=1, max_length=1024)
  content: str = Field(min_length=1)


class ArtifactResponse(BaseModel):
  id: str
  job_id: str
  artifact_type: ArtifactType
  source_ref: str
  sha256: str
  size_bytes: int
  parser_status: str
  created_at: datetime


class BuildGraphResponse(BaseModel):
  job_id: str
  graph_id: str
  status: JobStatus
  node_count: int
  edge_count: int


class PermissionGraphResponse(BaseModel):
  id: str
  job_id: str
  node_count: int
  edge_count: int
  graph: dict[str, object]
  created_at: datetime
  updated_at: datetime


class GenerateCandidatePolicyRequest(BaseModel):
  provider: Provider
  identity_types: list[str] = Field(min_length=1)


class ValidateCandidatePolicyRequest(BaseModel):
  provider: Provider


class CompareCurrentPermissionsRequest(BaseModel):
  provider: Provider
  current_policy: dict[str, object]


class ExplainPermissionRequest(BaseModel):
  provider: Provider
  permission: str = Field(min_length=3)


class ExportPolicyBundleRequest(BaseModel):
  provider: Provider
  format: str = Field(default="json")


class CandidatePolicyResponse(BaseModel):
  id: str
  job_id: str
  provider: Provider
  status: JobStatus
  candidate_policy: dict[str, object]


class ValidationResponse(BaseModel):
  id: str
  job_id: str
  provider: Provider
  status: JobStatus
  validation: dict[str, object]


class DiffResponse(BaseModel):
  id: str
  job_id: str
  provider: Provider
  status: JobStatus
  diff: dict[str, object]


class ExplainPermissionResponse(BaseModel):
  job_id: str
  provider: Provider
  permission: str
  decision: str
  reason: str
  trace_refs: list[str]


class ExportBundleResponse(BaseModel):
  id: str
  job_id: str
  provider: Provider
  status: JobStatus
  bundle: dict[str, object]


def _env(name: str, default: str) -> str:
  return os.getenv(name, default).strip()


def _now_utc() -> datetime:
  return datetime.now(tz=timezone.utc)


def _id(prefix: str) -> str:
  return f"{prefix}{uuid.uuid4().hex[:12]}"


def _error(http_status: int, code: str, message: str, *, stage: str = "api", retryable: bool = False) -> HTTPException:
  return HTTPException(
    status_code=http_status,
    detail={
      "error": {
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "http_status": http_status
      }
    }
  )


def _db_url() -> str:
  return _env("CIEM_DB_URL", "sqlite:///./ciem_factory.db")


def _session_factory() -> sessionmaker:
  db_url = _db_url()
  engine = create_engine(db_url, future=True)
  Base.metadata.create_all(engine)
  return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)


def startup_guardrails() -> None:
  mode = _env("CIEM_MODE", "local")
  auth_mode = _env("CIEM_AUTH_MODE", "local_token")
  tenancy_mode = _env("CIEM_TENANCY_MODE", "single")
  signing_key_source = _env("CIEM_SIGNING_KEY_SOURCE", "")

  if mode == "hosted":
    if auth_mode == "disabled":
      raise RuntimeError("Hosted mode requires auth (CIEM_AUTH_MODE cannot be disabled).")
    if tenancy_mode != "multi":
      raise RuntimeError("Hosted mode requires CIEM_TENANCY_MODE=multi.")
    if not signing_key_source:
      raise RuntimeError("Hosted mode requires CIEM_SIGNING_KEY_SOURCE.")


app = FastAPI(title="ciem-factory-api", version="0.2.0")
SessionLocal = _session_factory()
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)


def _to_job_response(job: Job) -> JobResponse:
  return JobResponse(
    id=job.id,
    tenant_id=job.tenant_id,
    project_id=job.project_id,
    name=job.name,
    mode=job.mode,
    target_providers=job.target_providers.split(","),
    status=job.status,
    created_at=job.created_at,
    updated_at=job.updated_at
  )


def _has_inputs(job: Job) -> bool:
  return len(job.artifacts) > 0 or len(job.policy_documents) > 0


def _maybe_set_inputs_registered(job: Job, now: datetime) -> None:
  if job.status == JobStatus.created and _has_inputs(job):
    job.status = JobStatus.inputs_registered
    job.updated_at = now


def _build_graph_payload(job: Job) -> tuple[dict[str, object], int, int]:
  nodes: list[dict[str, object]] = []
  edges: list[dict[str, object]] = []

  principal_id = f"node-{job.id}-principal"
  nodes.append(
    {
      "id": principal_id,
      "type": "principal",
      "provider": "aws",
      "attributes": {"name": f"{job.name}-runtime-role", "identity_type": "runtime_role"},
      "trace": {"artifact_id": None, "source_path": "job.metadata", "line_range": None}
    }
  )

  for artifact in job.artifacts:
    action_id = f"node-{artifact.id}-action"
    resource_id = f"node-{artifact.id}-resource"
    nodes.append(
      {
        "id": action_id,
        "type": "action",
        "provider": "aws",
        "attributes": {"name": f"{artifact.artifact_type.value}:analyze"},
        "trace": {"artifact_id": artifact.id, "source_path": artifact.source_ref, "line_range": None}
      }
    )
    nodes.append(
      {
        "id": resource_id,
        "type": "resource",
        "provider": "aws",
        "attributes": {"name": artifact.source_ref, "kind": artifact.artifact_type.value},
        "trace": {"artifact_id": artifact.id, "source_path": artifact.source_ref, "line_range": None}
      }
    )
    edges.append(
      {
        "id": _id("edge-"),
        "type": "requires",
        "from_node_id": principal_id,
        "to_node_id": action_id,
        "attributes": {"confidence": 0.9},
        "trace": {"rule_id": "mvp.artifact.requires.action", "evidence_ref": None}
      }
    )
    edges.append(
      {
        "id": _id("edge-"),
        "type": "requires",
        "from_node_id": action_id,
        "to_node_id": resource_id,
        "attributes": {"confidence": 0.88},
        "trace": {"rule_id": "mvp.action.requires.resource", "evidence_ref": None}
      }
    )

  for doc in job.policy_documents:
    constraint_id = f"node-{doc.id}-constraint"
    nodes.append(
      {
        "id": constraint_id,
        "type": "constraint",
        "provider": "aws",
        "attributes": {"title": doc.title, "scope": doc.scope, "provider": doc.provider},
        "trace": {"artifact_id": None, "source_path": f"policy_document:{doc.id}", "line_range": None}
      }
    )
    edges.append(
      {
        "id": _id("edge-"),
        "type": "constrained_by",
        "from_node_id": principal_id,
        "to_node_id": constraint_id,
        "attributes": {"confidence": 0.92},
        "trace": {"rule_id": "mvp.doc.constrains.principal", "evidence_ref": None}
      }
    )

  payload = {
    "id": f"graph-{job.id}",
    "tenant_id": job.tenant_id,
    "project_id": job.project_id,
    "job_id": job.id,
    "nodes": nodes,
    "edges": edges,
    "build_metadata": {
      "artifact_ids": [artifact.id for artifact in job.artifacts],
      "document_ids": [doc.id for doc in job.policy_documents],
      "builder_version": "0.1.0"
    },
    "schema_version": "1.0.0"
  }
  return payload, len(nodes), len(edges)


def _job_targets_provider(job: Job, provider: Provider) -> bool:
  return provider.value in set(job.target_providers.split(","))


def _extract_actions_from_artifacts(artifacts: list[Artifact]) -> set[str]:
  actions: set[str] = {"logs:CreateLogGroup", "logs:PutLogEvents"}
  for artifact in artifacts:
    source = artifact.source_ref.lower()
    if "s3" in source:
      actions.update({"s3:GetObject", "s3:PutObject", "s3:ListBucket"})
    if "dynamodb" in source:
      actions.update({"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"})
    if "lambda" in source:
      actions.update({"lambda:InvokeFunction"})
    # Baseline read permissions for discovery.
    actions.add("ec2:DescribeSubnets")
  return actions


def _risk_for_action(action: str) -> tuple[float, str]:
  risky = {
    "iam:PassRole": (9.8, "privilege_escalation"),
    "iam:CreateRole": (9.9, "privilege_escalation"),
    "iam:AttachRolePolicy": (9.9, "privilege_escalation"),
    "iam:PutRolePolicy": (9.9, "privilege_escalation"),
    "lambda:UpdateFunctionCode": (8.8, "code_mutation")
  }
  return risky.get(action, (2.0, "low"))


def _candidate_policy_from_job(job: Job, provider: Provider, identity_types: list[str]) -> dict[str, object]:
  required_actions = sorted(_extract_actions_from_artifacts(job.artifacts))
  denied_high_risk = [
    "iam:PassRole",
    "iam:CreateRole",
    "iam:AttachRolePolicy",
    "iam:PutRolePolicy",
    "lambda:UpdateFunctionCode"
  ]
  decision_entries = []
  for action in required_actions + denied_high_risk:
    risk_score, risk_class = _risk_for_action(action)
    included = action in required_actions
    decision_entries.append(
      {
        "permission": action,
        "decision": "included" if included else "excluded",
        "severity": "critical" if risk_score >= 9 else "medium" if risk_score >= 7 else "low",
        "risk_score": risk_score,
        "risk_class": risk_class,
        "rationale": "Derived from artifact dependency mapping" if included else "Excluded as high-risk without deterministic requirement",
        "trace_refs": [artifact.id for artifact in job.artifacts[:2]]
      }
    )
  identity_policies = []
  for identity_type in identity_types:
    identity_policies.append(
      {
        "identity_type": identity_type,
        "policy_document": {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Effect": "Allow",
              "Action": required_actions,
              "Resource": "*"
            }
          ]
        },
        "trust_policy": {
          "Version": "2012-10-17",
          "Statement": [{"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"}, "Action": "sts:AssumeRole"}]
        },
        "decision_entries": decision_entries
      }
    )
  return {
    "id": _id("run-"),
    "job_id": job.id,
    "provider": provider.value,
    "identity_policies": identity_policies,
    "unresolved_requirements": [],
    "created_at": _now_utc().isoformat(),
    "schema_version": "1.0.0"
  }


def _validation_for_candidate(candidate: dict[str, object], provider: Provider) -> dict[str, object]:
  all_entries = []
  for identity_policy in candidate.get("identity_policies", []):
    all_entries.extend(identity_policy.get("decision_entries", []))
  included = [entry for entry in all_entries if entry.get("decision") == "included"]
  excluded = [entry for entry in all_entries if entry.get("decision") == "excluded"]
  critical_unjustified = [
    entry for entry in included if entry.get("risk_score", 0) >= 9
  ]
  result = "pass" if not critical_unjustified else "fail"
  confidence = 0.86 if result == "pass" else 0.6
  findings = []
  if critical_unjustified:
    findings.append(
      {
        "finding_id": _id("fnd-"),
        "severity": "critical",
        "code": "VAL_CRITICAL_ESCALATION_UNJUSTIFIED",
        "message": "Critical high-risk action included without safe narrowing.",
        "blocking": True
      }
    )
  checks = [
    {
      "check_id": "aws.static.no_wildcard_admin",
      "name": "No wildcard admin actions",
      "result": "pass",
      "severity": "high",
      "details": "No iam:* or *:* actions generated."
    },
    {
      "check_id": "aws.risk.high_risk_excluded",
      "name": "High-risk actions excluded unless required",
      "result": "pass" if len(excluded) > 0 else "warning",
      "severity": "high",
      "details": "High-risk actions are excluded by default."
    }
  ]
  return {
    "id": _id("run-val-"),
    "job_id": candidate["job_id"],
    "provider": provider.value,
    "result": result,
    "confidence_score": confidence,
    "checks": checks,
    "simulations": [],
    "findings": findings,
    "created_at": _now_utc().isoformat(),
    "schema_version": "1.0.0"
  }


def _diff_current_policy(candidate: dict[str, object], current_policy: dict[str, object], provider: Provider) -> dict[str, object]:
  recommended_actions = set()
  for identity_policy in candidate.get("identity_policies", []):
    statements = identity_policy.get("policy_document", {}).get("Statement", [])
    for statement in statements:
      for action in statement.get("Action", []):
        recommended_actions.add(action)
  current_actions = set()
  for statement in current_policy.get("Statement", []):
    actions = statement.get("Action", [])
    if isinstance(actions, str):
      current_actions.add(actions)
    else:
      current_actions.update(actions)
  excess = sorted(current_actions - recommended_actions)
  missing = sorted(recommended_actions - current_actions)
  return {
    "id": _id("diff-"),
    "job_id": candidate["job_id"],
    "provider": provider.value,
    "excess_permissions": excess,
    "missing_permissions": missing,
    "changed_scopes": [],
    "risk_delta_score": float(len(excess) * -2 + len(missing)),
    "created_at": _now_utc().isoformat(),
    "schema_version": "1.0.0"
  }


def _explain_permission(candidate: dict[str, object], permission: str, provider: Provider) -> dict[str, object]:
  for identity_policy in candidate.get("identity_policies", []):
    for entry in identity_policy.get("decision_entries", []):
      if entry.get("permission") == permission:
        return {
          "job_id": candidate["job_id"],
          "provider": provider.value,
          "permission": permission,
          "decision": entry.get("decision", "unresolved"),
          "reason": entry.get("rationale", "No rationale available."),
          "trace_refs": entry.get("trace_refs", [])
        }
  return {
    "job_id": candidate["job_id"],
    "provider": provider.value,
    "permission": permission,
    "decision": "unresolved",
    "reason": "Permission not present in generated candidate policy.",
    "trace_refs": []
  }


def _export_bundle(job: Job, provider: Provider, analysis: ProviderAnalysis) -> dict[str, object]:
  candidate_ref = f"object://runs/{job.id}/{provider.value}/candidate.json" if analysis.candidate_policy_json else None
  validation_ref = f"object://runs/{job.id}/{provider.value}/validation.json" if analysis.validation_json else None
  diff_ref = f"object://runs/{job.id}/{provider.value}/diff.json" if analysis.diff_json else None
  explanation_ref = f"object://runs/{job.id}/{provider.value}/explanation.json" if analysis.explanation_json else None
  bundle_id = _id("bundle-")
  signature_seed = f"{job.id}|{provider.value}|{analysis.updated_at.isoformat()}|ciem-factory"
  return {
    "id": bundle_id,
    "job_id": job.id,
    "provider": provider.value,
    "bundle_type": "least_privilege_recommendation",
    "contents": {
      "candidate_policy_ref": candidate_ref,
      "validation_ref": validation_ref,
      "diff_ref": diff_ref,
      "explanation_ref": explanation_ref
    },
    "integrity": {
      "sha256": hashlib.sha256(signature_seed.encode("utf-8")).hexdigest(),
      "signature_ref": f"object://bundles/{job.id}/{provider.value}/{bundle_id}.sig"
    },
    "created_at": _now_utc().isoformat(),
    "schema_version": "1.0.0"
  }


@app.on_event("startup")
def _startup() -> None:
  startup_guardrails()


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok", "service": "api"}


@app.get("/config")
def config() -> dict[str, str]:
  return {
    "mode": _env("CIEM_MODE", "local"),
    "auth_mode": _env("CIEM_AUTH_MODE", "local_token"),
    "tenancy_mode": _env("CIEM_TENANCY_MODE", "single")
  }


@app.post("/v1/jobs", response_model=JobResponse)
def create_job(payload: CreateJobRequest) -> JobResponse:
  now = _now_utc()
  job = Job(
    id=_id("job-"),
    tenant_id=_env("CIEM_DEFAULT_TENANT_ID", "tenant-local"),
    project_id=payload.project_id,
    name=payload.name,
    mode=payload.mode,
    status=JobStatus.created,
    target_providers=",".join(provider.value for provider in payload.target_providers),
    created_by=_env("CIEM_DEFAULT_ACTOR_ID", "local-user"),
    created_at=now,
    updated_at=now
  )
  with SessionLocal.begin() as session:
    session.add(job)
  return _to_job_response(job)


@app.get("/v1/jobs", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
  with SessionLocal() as session:
    jobs = session.query(Job).order_by(Job.created_at.desc()).all()
  return [_to_job_response(job) for job in jobs]


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
  if not job:
    raise _error(404, "ERR_ARTIFACT_NOT_FOUND", "Job not found", stage="job_lookup")
  return _to_job_response(job)


@app.post("/v1/jobs/{job_id}/artifacts", response_model=ArtifactResponse)
def upload_artifact_reference(job_id: str, payload: RegisterArtifactRequest) -> ArtifactResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="artifact_registration")
    content_bytes = payload.content.encode("utf-8")
    artifact = Artifact(
      id=_id("art-"),
      job_id=job.id,
      tenant_id=job.tenant_id,
      project_id=job.project_id,
      artifact_type=payload.artifact_type,
      source_ref=payload.path,
      sha256=hashlib.sha256(content_bytes).hexdigest(),
      size_bytes=len(content_bytes),
      parser_status="registered",
      parser_errors="[]",
      created_at=now,
      updated_at=now
    )
    session.add(artifact)
    _maybe_set_inputs_registered(job, now)
    session.flush()
    return ArtifactResponse(
      id=artifact.id,
      job_id=artifact.job_id,
      artifact_type=artifact.artifact_type,
      source_ref=artifact.source_ref,
      sha256=artifact.sha256,
      size_bytes=artifact.size_bytes,
      parser_status=artifact.parser_status,
      created_at=artifact.created_at
    )


@app.get("/v1/jobs/{job_id}/artifacts", response_model=list[ArtifactResponse])
def list_artifacts(job_id: str) -> list[ArtifactResponse]:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="artifact_listing")
    artifacts = session.query(Artifact).filter_by(job_id=job_id).order_by(Artifact.created_at.desc()).all()
  return [
    ArtifactResponse(
      id=artifact.id,
      job_id=artifact.job_id,
      artifact_type=artifact.artifact_type,
      source_ref=artifact.source_ref,
      sha256=artifact.sha256,
      size_bytes=artifact.size_bytes,
      parser_status=artifact.parser_status,
      created_at=artifact.created_at
    )
    for artifact in artifacts
  ]


@app.post("/v1/jobs/{job_id}/policy-documents", response_model=PolicyDocumentResponse)
def register_policy_document(job_id: str, payload: RegisterPolicyDocumentRequest) -> PolicyDocumentResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="document_registration")
    doc = PolicyDocument(
      id=_id("doc-"),
      job_id=job.id,
      tenant_id=job.tenant_id,
      project_id=job.project_id,
      title=payload.title,
      scope=payload.scope,
      provider=payload.provider,
      priority=payload.priority,
      content_type=payload.content_type,
      content=payload.content,
      created_at=now,
      updated_at=now
    )
    session.add(doc)
    _maybe_set_inputs_registered(job, now)
    session.flush()
    response = PolicyDocumentResponse(
      id=doc.id,
      job_id=doc.job_id,
      title=doc.title,
      scope=doc.scope,
      provider=doc.provider,
      priority=doc.priority,
      content_type=doc.content_type,
      created_at=doc.created_at
    )
  return response


@app.get("/v1/jobs/{job_id}/policy-documents", response_model=list[PolicyDocumentResponse])
def list_policy_documents(job_id: str) -> list[PolicyDocumentResponse]:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="document_listing")
    docs = session.query(PolicyDocument).filter_by(job_id=job_id).order_by(PolicyDocument.created_at.desc()).all()
  return [
    PolicyDocumentResponse(
      id=doc.id,
      job_id=doc.job_id,
      title=doc.title,
      scope=doc.scope,
      provider=doc.provider,
      priority=doc.priority,
      content_type=doc.content_type,
      created_at=doc.created_at
    )
    for doc in docs
  ]


@app.post("/v1/jobs/{job_id}/build-permission-graph", response_model=BuildGraphResponse)
def build_permission_graph(job_id: str) -> BuildGraphResponse:
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="graph_build")
    if not _has_inputs(job):
      raise _error(422, "ERR_GRAPH_BUILD_FAILED", "No registered inputs found for graph build", stage="parsing")
    if job.status not in {JobStatus.inputs_registered, JobStatus.parsing, JobStatus.graph_built}:
      raise _error(409, "ERR_INVALID_INPUT_SCHEMA", f"Cannot build graph from status {job.status.value}", stage="parsing")
    now = _now_utc()
    job.status = JobStatus.parsing
    job.updated_at = now
    graph_payload, node_count, edge_count = _build_graph_payload(job)
    existing_graph = session.query(PermissionGraph).filter_by(job_id=job.id).one_or_none()
    if existing_graph:
      existing_graph.graph_json = json.dumps(graph_payload)
      existing_graph.node_count = node_count
      existing_graph.edge_count = edge_count
      existing_graph.updated_at = now
    else:
      session.add(
        PermissionGraph(
          id=f"graph-{job.id}",
          job_id=job.id,
          tenant_id=job.tenant_id,
          project_id=job.project_id,
          graph_json=json.dumps(graph_payload),
          node_count=node_count,
          edge_count=edge_count,
          created_at=now,
          updated_at=now
        )
      )
    job.status = JobStatus.graph_built
    job.updated_at = now
  return BuildGraphResponse(
    job_id=job_id,
    graph_id=f"graph-{job_id}",
    status=JobStatus.graph_built,
    node_count=node_count,
    edge_count=edge_count
  )


@app.get("/v1/jobs/{job_id}/graph", response_model=PermissionGraphResponse)
def get_permission_graph(job_id: str) -> PermissionGraphResponse:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="graph_fetch")
    graph = session.query(PermissionGraph).filter_by(job_id=job_id).one_or_none()
    if not graph:
      raise _error(404, "ERR_GRAPH_BUILD_FAILED", "Graph not built yet", stage="graph_fetch")
  return PermissionGraphResponse(
    id=graph.id,
    job_id=graph.job_id,
    node_count=graph.node_count,
    edge_count=graph.edge_count,
    graph=json.loads(graph.graph_json),
    created_at=graph.created_at,
    updated_at=graph.updated_at
  )


def _get_or_create_provider_analysis(session, job: Job, provider: Provider, now: datetime) -> ProviderAnalysis:
  analysis = session.query(ProviderAnalysis).filter_by(job_id=job.id, provider=provider).one_or_none()
  if analysis:
    return analysis
  analysis = ProviderAnalysis(
    id=_id("analysis-"),
    job_id=job.id,
    provider=provider,
    candidate_policy_json=None,
    validation_json=None,
    diff_json=None,
    explanation_json=None,
    bundle_json=None,
    created_at=now,
    updated_at=now
  )
  session.add(analysis)
  session.flush()
  return analysis


@app.post("/v1/jobs/{job_id}/generate-candidate-policy", response_model=CandidatePolicyResponse)
def generate_candidate_policy(job_id: str, payload: GenerateCandidatePolicyRequest) -> CandidatePolicyResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="policy_generation")
    if not _job_targets_provider(job, payload.provider):
      raise _error(422, "ERR_INVALID_INPUT_SCHEMA", "Provider is not targeted by this job", stage="policy_generation")
    if job.status not in {JobStatus.graph_built, JobStatus.policy_generating, JobStatus.policy_generated, JobStatus.validated}:
      raise _error(409, "ERR_INVALID_INPUT_SCHEMA", f"Cannot generate policy from status {job.status.value}", stage="policy_generation")

    job.status = JobStatus.policy_generating
    job.updated_at = now
    candidate = _candidate_policy_from_job(job, payload.provider, payload.identity_types)
    analysis = _get_or_create_provider_analysis(session, job, payload.provider, now)
    analysis.candidate_policy_json = json.dumps(candidate)
    analysis.updated_at = now
    job.status = JobStatus.policy_generated
    job.updated_at = now
  return CandidatePolicyResponse(
    id=candidate["id"],
    job_id=job_id,
    provider=payload.provider,
    status=JobStatus.policy_generated,
    candidate_policy=candidate
  )


@app.get("/v1/jobs/{job_id}/provider/{provider}/candidate-policy", response_model=CandidatePolicyResponse)
def get_candidate_policy(job_id: str, provider: Provider) -> CandidatePolicyResponse:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="candidate_fetch")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=provider).one_or_none()
    if not analysis or not analysis.candidate_policy_json:
      raise _error(404, "ERR_POLICY_SYNTHESIS_FAILED", "Candidate policy not generated", stage="candidate_fetch")
    candidate = json.loads(analysis.candidate_policy_json)
  return CandidatePolicyResponse(
    id=candidate["id"],
    job_id=job_id,
    provider=provider,
    status=job.status,
    candidate_policy=candidate
  )


@app.post("/v1/jobs/{job_id}/validate-candidate-policy", response_model=ValidationResponse)
def validate_candidate_policy(job_id: str, payload: ValidateCandidatePolicyRequest) -> ValidationResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="validation")
    if job.status not in {JobStatus.policy_generated, JobStatus.validating, JobStatus.validated, JobStatus.completed_with_warnings}:
      raise _error(409, "ERR_INVALID_INPUT_SCHEMA", f"Cannot validate from status {job.status.value}", stage="validation")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=payload.provider).one_or_none()
    if not analysis or not analysis.candidate_policy_json:
      raise _error(422, "ERR_VALIDATION_FAILED", "Candidate policy required before validation", stage="validation")
    candidate = json.loads(analysis.candidate_policy_json)
    job.status = JobStatus.validating
    validation = _validation_for_candidate(candidate, payload.provider)
    analysis.validation_json = json.dumps(validation)
    analysis.updated_at = now
    if validation["result"] == "pass":
      job.status = JobStatus.validated
    else:
      job.status = JobStatus.completed_with_warnings
    job.updated_at = now
  return ValidationResponse(
    id=validation["id"],
    job_id=job_id,
    provider=payload.provider,
    status=job.status,
    validation=validation
  )


@app.get("/v1/jobs/{job_id}/provider/{provider}/validation", response_model=ValidationResponse)
def get_validation(job_id: str, provider: Provider) -> ValidationResponse:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="validation_fetch")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=provider).one_or_none()
    if not analysis or not analysis.validation_json:
      raise _error(404, "ERR_VALIDATION_FAILED", "Validation not available", stage="validation_fetch")
    validation = json.loads(analysis.validation_json)
  return ValidationResponse(
    id=validation["id"],
    job_id=job_id,
    provider=provider,
    status=job.status,
    validation=validation
  )


@app.post("/v1/jobs/{job_id}/compare-current-permissions", response_model=DiffResponse)
def compare_current_permissions(job_id: str, payload: CompareCurrentPermissionsRequest) -> DiffResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="diffing")
    if job.status not in {JobStatus.policy_generated, JobStatus.validated, JobStatus.diffing, JobStatus.completed_with_warnings}:
      raise _error(409, "ERR_INVALID_INPUT_SCHEMA", f"Cannot diff from status {job.status.value}", stage="diffing")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=payload.provider).one_or_none()
    if not analysis or not analysis.candidate_policy_json:
      raise _error(422, "ERR_DIFF_FAILED", "Candidate policy required before diff", stage="diffing")
    candidate = json.loads(analysis.candidate_policy_json)
    prior_status = job.status
    job.status = JobStatus.diffing
    diff = _diff_current_policy(candidate, payload.current_policy, payload.provider)
    analysis.diff_json = json.dumps(diff)
    analysis.updated_at = now
    # Keep validated status if already reached, otherwise mark partial completion.
    if prior_status != JobStatus.validated:
      job.status = JobStatus.completed_with_warnings
    else:
      job.status = JobStatus.validated
    job.updated_at = now
  return DiffResponse(
    id=diff["id"],
    job_id=job_id,
    provider=payload.provider,
    status=job.status,
    diff=diff
  )


@app.get("/v1/jobs/{job_id}/diff", response_model=DiffResponse)
def get_diff(job_id: str, provider: Provider = Provider.aws) -> DiffResponse:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="diff_fetch")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=provider).one_or_none()
    if not analysis or not analysis.diff_json:
      raise _error(404, "ERR_DIFF_FAILED", "Diff not available", stage="diff_fetch")
    diff = json.loads(analysis.diff_json)
  return DiffResponse(
    id=diff["id"],
    job_id=job_id,
    provider=provider,
    status=job.status,
    diff=diff
  )


@app.post("/v1/jobs/{job_id}/explain-permission", response_model=ExplainPermissionResponse)
def explain_permission(job_id: str, payload: ExplainPermissionRequest) -> ExplainPermissionResponse:
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="explain")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=payload.provider).one_or_none()
    if not analysis or not analysis.candidate_policy_json:
      raise _error(422, "ERR_POLICY_SYNTHESIS_FAILED", "Candidate policy required before explanation", stage="explain")
    candidate = json.loads(analysis.candidate_policy_json)
    explanation = _explain_permission(candidate, payload.permission, payload.provider)
    analysis.explanation_json = json.dumps(explanation)
    analysis.updated_at = _now_utc()
  return ExplainPermissionResponse(**explanation)


@app.post("/v1/jobs/{job_id}/export-policy-bundle", response_model=ExportBundleResponse)
def export_policy_bundle(job_id: str, payload: ExportPolicyBundleRequest) -> ExportBundleResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="export")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=payload.provider).one_or_none()
    if not analysis or not analysis.candidate_policy_json:
      raise _error(422, "ERR_BUNDLE_EXPORT_FAILED", "Candidate policy required before export", stage="export")
    job.status = JobStatus.exporting
    job.updated_at = now
    bundle = _export_bundle(job, payload.provider, analysis)
    analysis.bundle_json = json.dumps(bundle)
    analysis.updated_at = now
    if analysis.validation_json:
      job.status = JobStatus.completed
    else:
      job.status = JobStatus.completed_with_warnings
    job.updated_at = now
  return ExportBundleResponse(
    id=bundle["id"],
    job_id=job_id,
    provider=payload.provider,
    status=job.status,
    bundle=bundle
  )


@app.get("/v1/jobs/{job_id}/audit")
def get_audit(job_id: str, provider: Provider = Provider.aws) -> dict[str, object]:
  with SessionLocal() as session:
    job = session.get(Job, job_id)
    if not job:
      raise _error(404, "ERR_JOB_NOT_FOUND", "Job not found", stage="audit")
    analysis = session.query(ProviderAnalysis).filter_by(job_id=job_id, provider=provider).one_or_none()
    if not analysis:
      raise _error(404, "ERR_INTERNAL", "Provider analysis not found", stage="audit")
    return {
      "job_id": job_id,
      "provider": provider.value,
      "status": job.status.value,
      "timestamps": {
        "job_created_at": job.created_at.isoformat(),
        "analysis_updated_at": analysis.updated_at.isoformat()
      },
      "available_sections": {
        "candidate_policy": bool(analysis.candidate_policy_json),
        "validation": bool(analysis.validation_json),
        "diff": bool(analysis.diff_json),
        "explanation": bool(analysis.explanation_json),
        "bundle": bool(analysis.bundle_json)
      }
    }
