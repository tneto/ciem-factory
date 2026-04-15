import enum
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Enum, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class JobStatus(str, enum.Enum):
  created = "created"
  inputs_registered = "inputs_registered"
  parsing = "parsing"
  graph_built = "graph_built"


class Provider(str, enum.Enum):
  aws = "aws"
  azure = "azure"
  gcp = "gcp"
  oci = "oci"


class AnalysisMode(str, enum.Enum):
  design_time = "design_time"
  runtime_rightsizing = "runtime_rightsizing"


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


class BuildGraphResponse(BaseModel):
  job_id: str
  graph_id: str
  status: JobStatus
  node_count: int
  edge_count: int


def _env(name: str, default: str) -> str:
  return os.getenv(name, default).strip()


def _now_utc() -> datetime:
  return datetime.now(tz=timezone.utc)


def _id(prefix: str) -> str:
  return f"{prefix}{uuid.uuid4().hex[:12]}"


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
    raise HTTPException(status_code=404, detail={"error": {"code": "ERR_JOB_NOT_FOUND", "message": "Job not found"}})
  return _to_job_response(job)


@app.post("/v1/jobs/{job_id}/policy-documents", response_model=PolicyDocumentResponse)
def register_policy_document(job_id: str, payload: RegisterPolicyDocumentRequest) -> PolicyDocumentResponse:
  now = _now_utc()
  with SessionLocal.begin() as session:
    job = session.get(Job, job_id)
    if not job:
      raise HTTPException(
        status_code=404,
        detail={"error": {"code": "ERR_JOB_NOT_FOUND", "message": "Job not found"}}
      )
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
    if job.status == JobStatus.created:
      job.status = JobStatus.inputs_registered
      job.updated_at = now
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
      raise HTTPException(
        status_code=404,
        detail={"error": {"code": "ERR_JOB_NOT_FOUND", "message": "Job not found"}}
      )
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
      raise HTTPException(
        status_code=404,
        detail={"error": {"code": "ERR_JOB_NOT_FOUND", "message": "Job not found"}}
      )
    if job.status not in {JobStatus.inputs_registered, JobStatus.parsing, JobStatus.graph_built}:
      raise HTTPException(
        status_code=409,
        detail={
          "error": {
            "code": "ERR_INVALID_STATE_TRANSITION",
            "message": f"Cannot build graph from status {job.status.value}"
          }
        }
      )
    now = _now_utc()
    job.status = JobStatus.graph_built
    job.updated_at = now
  return BuildGraphResponse(
    job_id=job_id,
    graph_id=f"graph-{job_id}",
    status=JobStatus.graph_built,
    node_count=24,
    edge_count=46
  )
