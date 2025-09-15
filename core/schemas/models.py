from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum

class RefType(str, Enum):
    FILE = "file"
    CARD = "card"
    CONFIG = "config"
    README = "readme"

class ToolType(str, Enum):
    API = "api"
    LIB = "lib"
    MCP = "mcp"

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ActionKind(str, Enum):
    SLACK = "slack"
    JIRA = "jira"
    EMAIL = "email"

class ActionStatus(str, Enum):
    OK = "ok"
    FAIL = "fail"

# Database Models
class Project(BaseModel):
    id: Optional[int] = None
    name: str
    repo_url: str
    default_branch: str = "main"

class Model(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    provider: str
    version: str
    license: Optional[str] = None
    source_url: Optional[str] = None
    repo_path: Optional[str] = None
    commit_sha: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class Dataset(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    version: str
    license: Optional[str] = None
    source_url: Optional[str] = None
    commit_sha: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class PromptBlob(BaseModel):
    id: Optional[int] = None
    sha: str
    content: str

class Prompt(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    version: str
    path: str
    commit_sha: Optional[str] = None
    blob_sha: str
    meta: Dict[str, Any] = Field(default_factory=dict)

class Tool(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    version: str
    type: ToolType
    spec: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)

class EvidenceChunk(BaseModel):
    id: Optional[int] = None
    project_id: int
    ref_type: RefType
    ref_path: str
    commit_sha: Optional[str] = None
    chunk_ix: int
    text: str
    token_count: int
    emb: Optional[List[float]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class BOM(BaseModel):
    id: Optional[int] = None
    project_id: int
    bom_json: Dict[str, Any]
    created_at: Optional[datetime] = None

class BOMDiff(BaseModel):
    id: Optional[int] = None
    project_id: int
    from_bom: int
    to_bom: int
    summary: Dict[str, Any]
    created_at: Optional[datetime] = None

class Policy(BaseModel):
    id: Optional[int] = None
    rule: str
    severity: Severity
    spec: Dict[str, Any] = Field(default_factory=dict)

class PolicyOverride(BaseModel):
    id: Optional[int] = None
    project_id: int
    rule: str
    until: datetime
    reason: str

class PolicyEvent(BaseModel):
    id: Optional[int] = None
    project_id: int
    severity: Severity
    rule: str
    artifact: Dict[str, Any]
    details: Dict[str, Any]
    dedupe_key: str
    created_at: Optional[datetime] = None

class Action(BaseModel):
    id: Optional[int] = None
    project_id: int
    kind: ActionKind
    payload: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    status: ActionStatus = ActionStatus.OK
    created_at: Optional[datetime] = None

# Unified Artifact Model for Runtime Normalization
class NormalizedArtifact(BaseModel):
    """Unified artifact model for both static and runtime discovery."""
    id: str  # Canonical ID: project:name:kind:provider:version
    kind: Literal["model", "dataset", "prompt", "tool"]
    name: str
    version: str
    provider: str
    license_spdx: Optional[str] = None
    file_path: str
    content_hash: str
    commit_sha: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Agent State Models
class ScanState(BaseModel):
    project: Project
    commit_sha: Optional[str] = None
    files: List[str] = Field(default_factory=list)
    hf_slugs: List[str] = Field(default_factory=list)
    models: List[Model] = Field(default_factory=list)
    datasets: List[Dataset] = Field(default_factory=list)
    prompts: List[Prompt] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)
    normalized_artifacts: List[NormalizedArtifact] = Field(default_factory=list)
    evidence_chunks: List[EvidenceChunk] = Field(default_factory=list)
    bom: Optional[BOM] = None
    diff: Optional[BOMDiff] = None
    policy_events: List[PolicyEvent] = Field(default_factory=list)
    file_candidates: List[Any] = Field(default_factory=list)
    actions: List[Any] = Field(default_factory=list)
    error: Optional[str] = None
    actions: List[Action] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None