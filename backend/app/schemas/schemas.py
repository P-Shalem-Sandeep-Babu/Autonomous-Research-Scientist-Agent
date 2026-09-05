from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "researcher"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    status: str
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
    feedback: Optional[str] = None

class CodeUpdateSchema(BaseModel):
    content: str

class LaTeXUpdateSchema(BaseModel):
    latex_source: str
