from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# Token & Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    mfa_required: bool = False
    message: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

# Password Reset Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)

# MFA Schemas
class MFASetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    message: str

class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class MFADisableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8, max_length=128)

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=128)
    role: str = "researcher"

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 characters)")

class UserResponse(UserBase):
    id: int
    created_at: datetime
    subscription_tier: str = "free"
    balance_usd: float = 25.0
    compute_quota_gpu_hours: float = 100.0
    compute_used_gpu_hours: float = 0.0
    token_quota: int = 500000
    token_used: int = 0
    mfa_enabled: bool = False

    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Project title (1-255 characters)")
    description: Optional[str] = Field(None, max_length=5000, description="Project research abstract or description (max 5000 characters)")

    @field_validator("title")
    @classmethod
    def validate_title_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project title cannot be empty or purely whitespace")
        return stripped

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    status: str
    current_stage: Optional[str] = "literature"
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Research Stage Schemas
class ResearchStageResponse(BaseModel):
    id: int
    project_id: int
    stage_name: str
    status: str
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reasoning_chain: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

# Literature Paper Schemas
class LiteraturePaperResponse(BaseModel):
    id: int
    project_id: int
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    methodology: Optional[str] = None
    findings: Optional[str] = None
    limitations: Optional[str] = None
    relevance_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# Research Gap Schemas
class ResearchGapResponse(BaseModel):
    id: int
    project_id: int
    description: str
    novelty_score: float
    opportunity_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# Hypothesis Schemas
class HypothesisResponse(BaseModel):
    id: int
    project_id: int
    statement: str
    reasoning: Optional[str] = None
    confidence_level: float
    selected: bool
    created_at: datetime

    class Config:
        from_attributes = True

class HypothesisSelect(BaseModel):
    hypothesis_id: int
    selected: bool

# Debate Log Schemas
class DebateLogResponse(BaseModel):
    id: int
    project_id: int
    hypothesis_id: int
    proposal_a: str
    proposal_b: str
    proposal_c: Optional[str] = None
    debate_rounds: Optional[List[Dict[str, Any]]] = None
    winner_proposal: Optional[str] = None
    rationale: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Dataset Recommendation Schemas
class DatasetRecommendationResponse(BaseModel):
    id: int
    project_id: int
    name: str
    source: Optional[str] = None
    url: Optional[str] = None
    quality_score: float
    description: Optional[str] = None
    metadata_fields: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Experiment Plan Schemas
class ExperimentPlanResponse(BaseModel):
    id: int
    project_id: int
    roadmap: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[List[Any]] = None
    hardware_requirements: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Generated File Schemas
class GeneratedFileResponse(BaseModel):
    id: int
    project_id: int
    filepath: str
    content: str
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Experiment Run Schemas
class ExperimentRunResponse(BaseModel):
    id: int
    project_id: int
    status: str
    logs: Optional[str] = None
    metrics_history: Optional[List[Dict[str, Any]]] = None
    plots: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Scientific Paper Schemas
class ScientificPaperResponse(BaseModel):
    id: int
    project_id: int
    title: str
    abstract: Optional[str] = None
    sections: Optional[Dict[str, str]] = None
    pdf_path: Optional[str] = None
    publication_readiness_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# Peer Review Schemas
class PeerReviewResponse(BaseModel):
    id: int
    paper_id: int
    score: float
    comments: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Knowledge Graph Node/Edge Schemas
class KnowledgeNodeSchema(BaseModel):
    id: str
    type: str
    label: str
    properties: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class KnowledgeEdgeSchema(BaseModel):
    source: str
    target: str
    type: str

    class Config:
        from_attributes = True

class KnowledgeGraphResponse(BaseModel):
    nodes: List[KnowledgeNodeSchema]
    edges: List[KnowledgeEdgeSchema]

# LLM Configuration Schema
class LLMConfig(BaseModel):
    provider: str  # gemini, openai, local
    model_name: str
    api_key: Optional[str] = None

class StageApproveSchema(BaseModel):
    is_approved: bool
    feedback: Optional[str] = Field(None, max_length=5000, description="Stage feedback (max 5000 characters)")

class CodeUpdateSchema(BaseModel):
    content: str = Field(..., min_length=1, max_length=500_000, description="Code source content (max 500 KB)")

class LaTeXUpdateSchema(BaseModel):
    latex_source: str = Field(..., min_length=1, max_length=1_000_000, description="LaTeX source document (max 1 MB)")

# Admin Schemas
class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime
    compute_quota_gpu_hours: float = 100.0
    compute_used_gpu_hours: float = 0.0
    is_active: bool = True
    projects_count: int = 0

    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    compute_quota_gpu_hours: Optional[float] = None
    is_active: Optional[bool] = None

class ApiKeyCreate(BaseModel):
    provider: str
    model: str
    key: str

class ApiKeyResponse(BaseModel):
    id: int
    provider: str
    model: str
    key: str
    status: str
    created_at: datetime
    last_used: Optional[datetime] = None

    class Config:
        from_attributes = True

class SystemComputeResponse(BaseModel):
    activeGpus: str
    allocatedCpuCores: int
    sharedSandboxRamGb: int
    virtualGpuLoadPct: int
    schedulerStatus: str

class SystemComputeUpdate(BaseModel):
    activeGpus: Optional[str] = None
    allocatedCpuCores: Optional[int] = None
    sharedSandboxRamGb: Optional[int] = None
    virtualGpuLoadPct: Optional[int] = None
    schedulerStatus: Optional[str] = None

# Billing & Commercial Operations Schemas
class BillingDepositRequest(BaseModel):
    amount_usd: float = Field(..., gt=0.0, description="Deposit amount in USD (must be > 0)")
    payment_method: str = Field(default="card_mock", description="Payment method token or provider")

class BillingSubscribeRequest(BaseModel):
    tier: str = Field(..., description="Target subscription tier: 'free', 'pro', or 'enterprise'")

class BillingTransactionResponse(BaseModel):
    id: int
    user_id: int
    amount_usd: float
    transaction_type: str
    status: str
    description: str
    reference_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BillingSummaryResponse(BaseModel):
    subscription_tier: str
    balance_usd: float
    compute_quota_gpu_hours: float
    compute_used_gpu_hours: float
    token_quota: int
    token_used: int
    transactions: List[BillingTransactionResponse] = []

# Audit Logging Schemas
class AuditLogResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Database Backup Schemas
class BackupItemResponse(BaseModel):
    filename: str
    size_bytes: int
    created_at: str
    sha256: str
    cloud_synced: bool

class BackupCreateRequest(BaseModel):
    label: str = Field(default="manual", max_length=50)

class BackupRestoreRequest(BaseModel):
    filename: str = Field(..., min_length=5, max_length=120)

class BackupRestoreResponse(BaseModel):
    status: str
    restored_from: str
    safety_backup: Optional[str] = None
    restored_at: str

# APM & Telemetry Schemas
class APMMetricsResponse(BaseModel):
    total_requests: int
    status_distribution: Dict[str, int]
    latency_ms: Dict[str, float]
    error_rate_pct: float
    recent_errors: List[Dict[str, Any]] = []



