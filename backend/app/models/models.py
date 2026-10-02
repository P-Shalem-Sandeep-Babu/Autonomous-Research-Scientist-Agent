from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean, JSON, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="researcher")  # researcher, supervisor, administrator
    compute_quota_gpu_hours = Column(Float, default=100.0)
    compute_used_gpu_hours = Column(Float, default=0.0)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    balance_usd = Column(Float, default=25.0)  # Initial trial balance in USD
    token_quota = Column(Integer, default=500_000)
    token_used = Column(Integer, default=0)
    stripe_customer_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    projects = relationship("Project", back_populates="user")
    transactions = relationship("BillingTransaction", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="idle", index=True)  # idle, running, completed, failed, paused, interrupted
    current_stage = Column(String, default="literature", nullable=True)
    checkpoint_data = Column(JSON, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    user = relationship("User", back_populates="projects")
    stages = relationship("ResearchStage", back_populates="project", cascade="all, delete-orphan")
    papers = relationship("LiteraturePaper", back_populates="project", cascade="all, delete-orphan")
    uploaded_papers = relationship("UploadedPaper", back_populates="project", cascade="all, delete-orphan")
    gaps = relationship("ResearchGap", back_populates="project", cascade="all, delete-orphan")
    hypotheses = relationship("Hypothesis", back_populates="project", cascade="all, delete-orphan")
    debate_logs = relationship("DebateLog", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("DatasetRecommendation", back_populates="project", cascade="all, delete-orphan")
    plans = relationship("ExperimentPlan", back_populates="project", cascade="all, delete-orphan")
    files = relationship("GeneratedFile", back_populates="project", cascade="all, delete-orphan")
    experiment_runs = relationship("ExperimentRun", back_populates="project", cascade="all, delete-orphan")
    scientific_papers = relationship("ScientificPaper", back_populates="project", cascade="all, delete-orphan")
    memories = relationship("ResearchMemory", back_populates="project", cascade="all, delete-orphan")
    reach_evidence = relationship("AgentReachEvidence", back_populates="project", cascade="all, delete-orphan")
    nodes = relationship("KnowledgeNode", back_populates="project", cascade="all, delete-orphan")
    edges = relationship("KnowledgeEdge", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")

class ResearchStage(Base):
    __tablename__ = "research_stages"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    stage_name = Column(String, nullable=False, index=True)  # literature, gap, hypothesis, debate, dataset, planning, coding, execution, evaluation, writing, review, memory, graph
    status = Column(String, default="pending", index=True)  # pending, active, completed, failed, paused
    output_data = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    is_approved = Column(Boolean, default=False)
    user_feedback = Column(Text, nullable=True)
    reasoning_chain = Column(JSON, nullable=True)  # List of CoT reasoning steps
    
    project = relationship("Project", back_populates="stages")

class LiteraturePaper(Base):
    __tablename__ = "literature_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    authors = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    source = Column(String, nullable=True)  # arXiv, PubMed, etc.
    methodology = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    relevance_score = Column(Numeric(5, 2), default=0.0)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="papers")

class ResearchGap(Base):
    __tablename__ = "research_gaps"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    description = Column(Text, nullable=False)
    novelty_score = Column(Numeric(5, 2), default=0.0)
    opportunity_score = Column(Numeric(5, 2), default=0.0)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="gaps")

class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    statement = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    confidence_level = Column(Numeric(5, 4), default=0.0)
    selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="hypotheses")
    debate_logs = relationship("DebateLog", back_populates="hypothesis", cascade="all, delete-orphan")

class DebateLog(Base):
    __tablename__ = "debate_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    hypothesis_id = Column(Integer, ForeignKey("hypotheses.id", ondelete="CASCADE"), index=True)
    proposal_a = Column(Text, nullable=False)
    proposal_b = Column(Text, nullable=False)
    proposal_c = Column(Text, nullable=True)
    debate_rounds = Column(JSON, nullable=True)  # List of messages from different debaters
    winner_proposal = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="debate_logs")
    hypothesis = relationship("Hypothesis", back_populates="debate_logs")

class DatasetRecommendation(Base):
    __tablename__ = "dataset_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name = Column(String, nullable=False)
    source = Column(String, nullable=True)  # Kaggle, HF, etc.
    url = Column(String, nullable=True)
    quality_score = Column(Numeric(5, 2), default=0.0)
    description = Column(Text, nullable=True)
    metadata_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="datasets")

class ExperimentPlan(Base):
    __tablename__ = "experiment_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    roadmap = Column(JSON, nullable=True)  # roadmap steps
    metrics = Column(JSON, nullable=True)  # list of target metrics
    hardware_requirements = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="plans")

class GeneratedFile(Base):
    __tablename__ = "generated_files"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filepath = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="files")

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    status = Column(String, default="running")  # running, completed, failed
    logs = Column(Text, nullable=True)
    metrics_history = Column(JSON, nullable=True)  # list of metric updates
    plots = Column(JSON, nullable=True)  # plot configs/values
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="experiment_runs")

class ScientificPaper(Base):
    __tablename__ = "scientific_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    abstract = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)  # dict of section titles to section contents
    pdf_path = Column(String, nullable=True)
    publication_readiness_score = Column(Numeric(5, 2), default=0.0)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="scientific_papers")
    peer_reviews = relationship("PeerReview", back_populates="paper", cascade="all, delete-orphan")

class PeerReview(Base):
    __tablename__ = "peer_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("scientific_papers.id", ondelete="CASCADE"), index=True)
    score = Column(Numeric(5, 2), default=0.0)
    comments = Column(JSON, nullable=True)  # dict of sections/critiques
    suggestions = Column(JSON, nullable=True)  # list of suggestions
    created_at = Column(DateTime, default=utc_now)
    
    paper = relationship("ScientificPaper", back_populates="peer_reviews")

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    
    id = Column(String, primary_key=True)  # Custom unique ID, e.g. "paper-1", "gap-3"
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    type = Column(String, nullable=False, index=True)  # paper, gap, hypothesis, dataset, experiment, code
    label = Column(String, nullable=False)
    properties = Column(JSON, nullable=True)
    
    project = relationship("Project", back_populates="nodes")

class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source = Column(String, nullable=False, index=True)
    target = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # addresses, refines, validates, uses, tests
    
    project = relationship("Project", back_populates="edges")

class ResearchMemory(Base):
    __tablename__ = "research_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    memory_type = Column(String, nullable=False, index=True)  # successful_method, failed_method, key_insight
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="memories")

class AgentReachEvidence(Base):
    __tablename__ = "agent_reach_evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source = Column(String, nullable=False)  # GitHub, Reddit, RSS, YouTube, TechBlog
    title = Column(String, nullable=False)
    url = Column(String, nullable=True)
    evidence_score = Column(Numeric(5, 2), default=0.0)
    community_sentiment = Column(Numeric(5, 2), default=0.0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="reach_evidence")

class UploadedPaper(Base):
    __tablename__ = "uploaded_papers"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename = Column(String, nullable=False)
    content_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    
    project = relationship("Project", back_populates="uploaded_papers")

class ApiKeyConfig(Base):
    __tablename__ = "api_key_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)  # Gemini Pro, OpenAI GPT-4o, etc.
    model_name = Column(String, nullable=False)
    masked_key = Column(String, nullable=False)
    status = Column(String, default="active")  # active, revoked
    created_at = Column(DateTime, default=utc_now)
    last_used = Column(DateTime, nullable=True)

class SystemComputeConfig(Base):
    __tablename__ = "system_compute_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    active_gpus = Column(String, default="1x NVIDIA A100 (80GB)")
    allocated_cpu_cores = Column(Integer, default=16)
    memory_limit_gb = Column(Integer, default=64)
    utilization_pct = Column(Integer, default=45)
    scheduler_status = Column(String, default="online")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class BillingTransaction(Base):
    __tablename__ = "billing_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_usd = Column(Float, nullable=False)  # Positive for topup, negative for run usage
    transaction_type = Column(String, nullable=False, index=True)  # "deposit", "pipeline_run", "subscription_charge", "refund"
    status = Column(String, default="completed", index=True)  # "completed", "pending", "failed"
    description = Column(String, nullable=False)
    reference_id = Column(String, nullable=True, index=True)  # Project ID, invoice ID, or payment intent
    created_at = Column(DateTime, default=utc_now)
    
    user = relationship("User", back_populates="transactions")

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String, nullable=False, index=True)
    doc_id = Column(String, nullable=False, index=True)
    text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    embedding_json = Column(JSON, nullable=False)  # Stored as serialized float array
    created_at = Column(DateTime, default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)  # e.g., "sandbox_command", "file_write", "code_update", "stage_approved", "auth_login"
    resource = Column(String, nullable=True)             # e.g., file path, stage name, or command
    details = Column(JSON, nullable=True)                # Structured JSON metadata (exit_code, ip, diff, etc.)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)

    project = relationship("Project", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")


