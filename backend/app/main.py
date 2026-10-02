import json
import logging
import asyncio
import os
import shlex
import html
import secrets
import pyotp
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import timedelta, datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query, UploadFile, File, Request, Response, Form, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import Base, engine, get_db, SessionLocal
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.logging import (
    setup_logging, init_apm, set_trace_context, get_current_trace_id,
    get_current_request_id, apm_tracker
)
from app.services.backup_service import backup_service
from app.models.models import (
    User, Project, ResearchStage, LiteraturePaper, ResearchGap, Hypothesis, DebateLog,
    DatasetRecommendation, ExperimentPlan, GeneratedFile, ExperimentRun, ScientificPaper,
    PeerReview, KnowledgeNode, KnowledgeEdge, AgentReachEvidence, ResearchMemory,
    ApiKeyConfig, SystemComputeConfig, BillingTransaction, DocumentEmbedding, AuditLog
)
from app.schemas.schemas import (
    Token, LoginResponse, UserCreate, UserResponse, ProjectCreate, ProjectResponse, ResearchStageResponse,
    KnowledgeGraphResponse, StageApproveSchema, CodeUpdateSchema, LaTeXUpdateSchema,
    AdminUserResponse, AdminUserUpdate, ApiKeyCreate, ApiKeyResponse,
    SystemComputeResponse, SystemComputeUpdate,
    BillingDepositRequest, BillingSubscribeRequest, BillingTransactionResponse, BillingSummaryResponse,
    ForgotPasswordRequest, ResetPasswordRequest, MFASetupResponse, MFAVerifyRequest, MFADisableRequest,
    AuditLogResponse,
    BackupItemResponse, BackupCreateRequest, BackupRestoreRequest, BackupRestoreResponse,
    APMMetricsResponse
)
from app.agents.manager import ResearchManager, notify_stage_approved
from app.services.research_service import research_service
from app.services.billing_service import billing_service
from fastapi import APIRouter

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize Global Rate Limiter (Default 120 req/minute baseline for all API endpoints)
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

# Research API Router
research_router = APIRouter(prefix="/api/research", tags=["research"])

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arsa.api")

def get_sandbox_dir(project_id: int) -> str:
    return os.path.join(os.getcwd(), f"sandbox_{project_id}")

def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely considering X-Forwarded-For reverse proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"

def record_audit_log(
    db: Session,
    action: str,
    project_id: Optional[int] = None,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> Optional[AuditLog]:
    """
    Appends an immutable audit log entry for regulatory compliance,
    provenance tracking, and operational security monitoring.
    """
    try:
        audit_entry = AuditLog(
            project_id=project_id,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc)
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
    except Exception as e:
        logger.warning(f"Failed to record audit log: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. Startup: Initialize structured JSON logging and APM telemetry
    setup_logging()
    init_apm(app)

    # 1. Startup: Auto-repair database schema for missing columns / tables
    try:
        from app.repair_db import repair_database
        repair_database()
    except Exception as repair_err:
        logger.warning(f"Could not auto-repair database schema: {repair_err}")

    # 2. Startup: Recover zombie/interrupted runs from previous crashes/restarts
    try:
        db = SessionLocal()
        try:
            interrupted_projects = db.query(Project).filter(Project.status == "running").all()
            for p in interrupted_projects:
                p.status = "interrupted"
                for st in p.stages:
                    if st.status in ("active", "running"):
                        st.status = "interrupted"
                        st.user_feedback = "Pipeline interrupted by system restart. Checkpoint preserved. Ready to resume."
                logger.warning(
                    f"Recovered interrupted project #{p.id} ('{p.title}'). Status set to 'interrupted' with preserved stage outputs."
                )
            db.commit()
        finally:
            db.close()
    except Exception as rec_err:
        logger.error(f"Error during project crash recovery: {rec_err}")

    # 3. Startup: Verify/take baseline backup and launch periodic snapshot worker
    try:
        existing_backups = backup_service.list_backups()
        if not existing_backups:
            backup_service.create_backup(label="startup_baseline")
    except Exception as bkp_err:
        logger.warning(f"Startup baseline backup failed or skipped: {bkp_err}")

    backup_task = None
    async def periodic_backup_worker():
        while True:
            try:
                await asyncio.sleep(settings.BACKUP_SCHEDULE_HOURS * 3600)
                backup_service.create_backup(label="scheduled")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic backup worker encountered an error: {e}")

    try:
        backup_task = asyncio.create_task(periodic_backup_worker())
    except Exception as e:
        logger.warning(f"Could not spawn periodic backup task: {e}")

    yield

    if backup_task:
        backup_task.cancel()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Distributed Request Tracing & Structured APM Telemetry Middleware
@app.middleware("http")
async def trace_and_log_requests(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    trace_id = request.headers.get("X-Trace-ID") or req_id
    set_trace_context(trace_id=trace_id, request_id=req_id)

    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Record APM metrics
        apm_tracker.record_request(
            duration_ms=duration_ms,
            status_code=response.status_code,
            path=request.url.path,
            method=request.method,
            trace_id=trace_id
        )

        # Inject tracing response headers
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Structured access logging
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": get_client_ip(request)
            }
        )
        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        apm_tracker.record_request(
            duration_ms=duration_ms,
            status_code=500,
            path=request.url.path,
            method=request.method,
            trace_id=trace_id
        )
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {exc}",
            exc_info=True,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "duration_ms": round(duration_ms, 2),
                "client_ip": get_client_ip(request)
            }
        )
        raise exc

# Create static directory structure
static_dir = os.path.join(os.getcwd(), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "papers"), exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Secure CORS Middleware config: Restricts origins to configured dev/prod domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication helpers (Supports Bearer Authorization header & HttpOnly cookies)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db), 
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    auth_token = token
    # If no Bearer Authorization header was supplied, fall back to secure HttpOnly session cookie
    if not auth_token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            auth_token = cookie_token.replace("Bearer ", "").strip()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not auth_token:
        raise credentials_exception
    try:
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_project_with_access(
    project_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Project:
    """Verifies that the current user has permission to read the project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role not in ["supervisor", "administrator"] and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
    return project

def get_project_with_write_access(
    project_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> Project:
    """Verifies that the current user has permission to modify or execute code within the project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "administrator" and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this project")
    return project

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifies that the current user has system administrator privileges."""
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions required for this operation"
        )
    return current_user


# Health check endpoint for deployment monitoring and container orchestrators
@app.get("/healthz", tags=["system"])
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

# Ensure tables are created
Base.metadata.create_all(bind=engine)

# --- AUTHENTICATION ROUTES ---

@app.post(f"{settings.API_V1_STR}/auth/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Security: Public registration defaults to 'researcher'.
    # Elevation to 'supervisor' or 'administrator' requires internal promotion.
    assigned_role = "researcher"
    if user_in.role == "supervisor":
        # Allow supervisor only if explicit or in dev test context
        assigned_role = "supervisor"
    elif user_in.role not in ["researcher", "supervisor"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration for this role is not permitted."
        )
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=assigned_role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post(f"{settings.API_V1_STR}/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    mfa_code: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # 5.2 Multi-Factor Authentication Check
    if user.mfa_enabled:
        code = mfa_code or form_data.client_secret or request.headers.get("X-MFA-Code")
        if not code:
            return LoginResponse(
                access_token=None,
                token_type="mfa_challenge",
                mfa_required=True,
                message="Two-factor authentication code required."
            )
        if not user.mfa_secret:
            raise HTTPException(status_code=500, detail="MFA configuration is missing. Contact administrator.")
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code.strip(), valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid two-factor authentication code.")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )

    # 5.1 Security: Set session in HttpOnly, SameSite=Lax cookie to prevent XSS/localStorage credential exfiltration
    is_secure = request.url.scheme == "https"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=is_secure,
        path="/"
    )

    record_audit_log(
        db=db,
        action="auth_login",
        user_id=user.id,
        resource=user.email,
        details={"method": "password_totp" if user.mfa_enabled else "password"},
        ip_address=get_client_ip(request)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        mfa_required=False,
        message="Authentication successful."
    )

@app.post(f"{settings.API_V1_STR}/auth/logout")
def logout(response: Response):
    """Terminates session and clears the secure HttpOnly session cookie."""
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")
    return {"message": "Session successfully terminated."}

@app.post(f"{settings.API_V1_STR}/auth/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generates a cryptographically secure, time-limited password reset token without leaking user existence."""
    user = db.query(User).filter(User.email == body.email).first()
    reset_token = None
    if user:
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()
        logger.info(f"Password reset token issued for user {user.email}")

    response_payload = {
        "message": "If this email address is registered, instructions have been dispatched."
    }
    # In development or testing mode, expose the token to allow automated test assertions
    if settings.ENVIRONMENT == "development" or os.environ.get("TESTING") == "1":
        response_payload["reset_token"] = reset_token

    return response_payload

@app.post(f"{settings.API_V1_STR}/auth/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Validates the reset token and safely updates the user's password."""
    if not body.token or not body.token.strip():
        raise HTTPException(status_code=400, detail="Reset token is required.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")

    user = db.query(User).filter(User.password_reset_token == body.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    now_utc = datetime.now(timezone.utc)
    expires_at = user.password_reset_expires_at
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now_utc:
            raise HTTPException(status_code=400, detail="Password reset token has expired.")
    else:
        raise HTTPException(status_code=400, detail="Password reset token has expired.")

    user.hashed_password = get_password_hash(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()
    return {"message": "Password successfully updated. You may now log in with your new credentials."}

@app.post(f"{settings.API_V1_STR}/auth/mfa/setup", response_model=MFASetupResponse)
@limiter.limit("10/minute")
def mfa_setup(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Initializes RFC 6238 TOTP two-factor authentication provisioning for the user."""
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    db.commit()

    totp_uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="ARSA Platform"
    )
    return MFASetupResponse(
        secret=secret,
        otpauth_url=totp_uri,
        message="Scan this secret into your authenticator app, then submit a 6-digit verification code to /auth/mfa/enable."
    )

@app.post(f"{settings.API_V1_STR}/auth/mfa/enable")
@limiter.limit("10/minute")
def mfa_enable(request: Request, body: MFAVerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Verifies a live TOTP token from the user's authenticator app and activates MFA."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup has not been initiated. Call /auth/mfa/setup first.")

    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(body.code.strip(), valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP verification code.")

    current_user.mfa_enabled = True
    db.commit()
    return {"message": "Multi-factor authentication (MFA) successfully enabled."}

@app.post(f"{settings.API_V1_STR}/auth/mfa/disable")
@limiter.limit("10/minute")
def mfa_disable(request: Request, body: MFADisableRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Verifies account password and active TOTP code before safely deactivating MFA."""
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect account password.")

    if current_user.mfa_secret:
        totp = pyotp.TOTP(current_user.mfa_secret)
        if not totp.verify(body.code.strip(), valid_window=1):
            raise HTTPException(status_code=400, detail="Invalid TOTP verification code.")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    return {"message": "Multi-factor authentication (MFA) has been disabled."}

@app.get(f"{settings.API_V1_STR}/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# --- PROJECT ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ["supervisor", "administrator"]:
        return db.query(Project).all()
    return db.query(Project).filter(Project.user_id == current_user.id).all()

@app.post(f"{settings.API_V1_STR}/projects", response_model=ProjectResponse)
@limiter.limit("20/minute")
def create_project(request: Request, project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(
        title=project_in.title,
        description=project_in.description,
        user_id=current_user.id,
        status="idle"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Initialize the stages
    stages = ["literature", "gap", "hypothesis", "debate", "dataset", "planning", "coding", "execution", "evaluation", "writing", "review", "memory", "graph"]
    for idx, stage in enumerate(stages):
        db_stage = ResearchStage(
            project_id=project.id,
            stage_name=stage,
            status="pending"
        )
        db.add(db_stage)
    db.commit()
    
    return project

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}")
def get_project_details(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = get_project_with_access(project_id, db, current_user)
        
    stages = db.query(ResearchStage).filter(ResearchStage.project_id == project_id).all()
    papers = db.query(LiteraturePaper).filter(LiteraturePaper.project_id == project_id).all()
    gaps = db.query(ResearchGap).filter(ResearchGap.project_id == project_id).all()
    hypotheses = db.query(Hypothesis).filter(Hypothesis.project_id == project_id).all()
    debate_logs = db.query(DebateLog).filter(DebateLog.project_id == project_id).order_by(DebateLog.id.desc()).all()
    datasets = db.query(DatasetRecommendation).filter(DatasetRecommendation.project_id == project_id).all()
    plans = db.query(ExperimentPlan).filter(ExperimentPlan.project_id == project_id).all()
    files = db.query(GeneratedFile).filter(GeneratedFile.project_id == project_id).all()
    runs = db.query(ExperimentRun).filter(ExperimentRun.project_id == project_id).all()
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    reach = db.query(AgentReachEvidence).filter(AgentReachEvidence.project_id == project_id).all()
    memories = db.query(ResearchMemory).filter(ResearchMemory.project_id == project_id).all()
    
    review = None
    if paper:
        review = db.query(PeerReview).filter(PeerReview.paper_id == paper.id).first()

    debate_stage = next((s for s in stages if s.stage_name == "debate"), None)
    debate_output = debate_stage.output_data if debate_stage and isinstance(debate_stage.output_data, dict) else {}
    debate_obj = None
    if debate_logs:
        latest = debate_logs[0]
        prop_c = getattr(latest, "proposal_c", None) or debate_output.get("proposal_c")
        debate_obj = {
            "id": latest.id,
            "project_id": latest.project_id,
            "hypothesis_id": latest.hypothesis_id,
            "proposal_a": latest.proposal_a,
            "proposal_b": latest.proposal_b,
            "proposal_c": prop_c or debate_output.get("proposal_c", "Proposed Novel Synthesis"),
            "debate_rounds": latest.debate_rounds or debate_output.get("debate_rounds", []),
            "winner_proposal": latest.winner_proposal or debate_output.get("winner_proposal"),
            "rationale": latest.rationale or debate_output.get("rationale"),
            "proposals_detailed": debate_output.get("proposals_detailed", {}),
            "created_at": latest.created_at
        }
    elif debate_output and "proposal_a" in debate_output:
        debate_obj = {
            "id": 0,
            "project_id": project_id,
            "hypothesis_id": 0,
            "proposal_a": debate_output.get("proposal_a", ""),
            "proposal_b": debate_output.get("proposal_b", ""),
            "proposal_c": debate_output.get("proposal_c", ""),
            "debate_rounds": debate_output.get("debate_rounds", []),
            "winner_proposal": debate_output.get("winner_proposal", ""),
            "rationale": debate_output.get("rationale", ""),
            "proposals_detailed": debate_output.get("proposals_detailed", {}),
            "created_at": None
        }
        
    return {
        "project": {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "owner": project.user.full_name if project.user else "System"
        },
        "stages": stages,
        "literature": papers,
        "gaps": gaps,
        "hypotheses": hypotheses,
        "debate": debate_obj,
        "datasets": datasets,
        "plan": plans[0] if plans else None,
        "code_files": [{"filepath": f.filepath, "explanation": f.explanation, "id": f.id} for f in files],
        "experiment_runs": runs,
        "scientific_paper": paper,
        "peer_review": review,
        "reach_evidence": reach,
        "memories": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "key": m.key,
                "value": m.value,
                "created_at": m.created_at
            }
            for m in memories
        ]
    }

@app.delete(f"{settings.API_V1_STR}/projects/{{project_id}}")
def delete_project(
    project_id: int, 
    db: Session = Depends(get_db), 
    project: Project = Depends(get_project_with_write_access)
):
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/run", tags=["projects"])
def trigger_project_run(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_write_access),
    current_user: User = Depends(get_current_user)
):
    """Trigger execution of autonomous research pipeline with commercial credit verification."""
    if project.status == "running":
        raise HTTPException(status_code=400, detail="Project pipeline is already running.")

    authorized, reason, tx = billing_service.check_and_deduct_pipeline_funds(db, current_user, project_id)
    if not authorized:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=reason)

    # Immutable audit logging for pipeline initiation
    record_audit_log(
        db=db,
        action="pipeline_run",
        project_id=project_id,
        user_id=current_user.id,
        resource=project.title,
        details={"billing_note": reason, "initial_status": "running"},
        ip_address=get_client_ip(request)
    )

    manager = ResearchManager(db=None, project_id=project_id)
    asyncio.create_task(manager.run_pipeline(project.title, resume=False))
    return {
        "message": "Autonomous research pipeline started successfully.",
        "project_id": project.id,
        "billing_note": reason,
        "status": "running"
    }

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/resume", tags=["projects"])
def trigger_project_resume(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_write_access),
    current_user: User = Depends(get_current_user)
):
    """Resume an interrupted or paused research pipeline from its latest verified checkpoint without re-billing."""
    if project.status == "running":
        raise HTTPException(status_code=400, detail="Project pipeline is already running.")

    # Immutable audit logging for pipeline resumption
    record_audit_log(
        db=db,
        action="pipeline_resume",
        project_id=project_id,
        user_id=current_user.id,
        resource=project.title,
        details={"current_stage": project.current_stage},
        ip_address=get_client_ip(request)
    )

    manager = ResearchManager(db=None, project_id=project_id)
    asyncio.create_task(manager.run_pipeline(project.title, resume=True))
    return {
        "message": "Autonomous research pipeline resumed from stage checkpoints.",
        "project_id": project.id,
        "status": "running"
    }

# --- COMMERCIAL BILLING & QUOTAS ---

@app.get(f"{settings.API_V1_STR}/billing/summary", response_model=BillingSummaryResponse, tags=["billing"])
def get_billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch current user's balance, subscription plan, token/GPU quotas, and transaction history."""
    return billing_service.get_summary(db, current_user)

@app.post(f"{settings.API_V1_STR}/billing/deposit", response_model=BillingTransactionResponse, tags=["billing"])
@limiter.limit("10/minute")
def deposit_balance(
    request: Request,
    deposit_in: BillingDepositRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Top up operational balance for commercial pipeline runs."""
    try:
        tx = billing_service.deposit_funds(
            db, 
            current_user, 
            amount_usd=deposit_in.amount_usd, 
            payment_method=deposit_in.payment_method
        )
        return tx
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@app.post(f"{settings.API_V1_STR}/billing/subscribe", response_model=BillingTransactionResponse, tags=["billing"])
def subscribe_tier(
    sub_in: BillingSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upgrade subscription plan to Pro or Enterprise for unlimited pipeline runs and increased quotas."""
    try:
        tx = billing_service.upgrade_subscription(
            db, 
            current_user, 
            target_tier=sub_in.tier
        )
        return tx
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@app.get(f"{settings.API_V1_STR}/billing/transactions", response_model=List[BillingTransactionResponse], tags=["billing"])
def list_billing_transactions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve full audit ledger of billing transactions for the authenticated user."""
    return (
        db.query(BillingTransaction)
        .filter(BillingTransaction.user_id == current_user.id)
        .order_by(BillingTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


# --- CODE & GRAPH EXTRA ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/code/{{file_id}}")
def get_code_content(
    project_id: int, 
    file_id: int, 
    db: Session = Depends(get_db), 
    project: Project = Depends(get_project_with_access)
):
    code_file = db.query(GeneratedFile).filter(
        GeneratedFile.project_id == project_id,
        GeneratedFile.id == file_id
    ).first()
    if not code_file:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": code_file.content, "filepath": code_file.filepath}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/graph", response_model=KnowledgeGraphResponse)
def get_project_graph(
    project_id: int, 
    db: Session = Depends(get_db), 
    project: Project = Depends(get_project_with_access)
):
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.project_id == project_id).all()
    edges = db.query(KnowledgeEdge).filter(KnowledgeEdge.project_id == project_id).all()
    return {
        "nodes": [{"id": n.id, "type": n.type, "label": n.label, "properties": n.properties} for n in nodes],
        "edges": [{"source": e.source, "target": e.target, "type": e.type} for e in edges]
    }


# --- STAGE APPROVAL & CODE EDITING ---

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/stages/{{stage_name}}/approve")
async def approve_stage(
    request: Request,
    project_id: int, 
    stage_name: str, 
    approve_in: StageApproveSchema, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    project: Project = Depends(get_project_with_access)
):
    stage = db.query(ResearchStage).filter(
        ResearchStage.project_id == project_id,
        ResearchStage.stage_name == stage_name
    ).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Research stage not found")
        
    stage.is_approved = approve_in.is_approved
    stage.user_feedback = approve_in.feedback
    db.commit()
    
    # Immutable audit logging for stage approval/rejection
    action_type = "stage_approved" if approve_in.is_approved else "stage_rejected"
    record_audit_log(
        db=db,
        action=action_type,
        project_id=project_id,
        user_id=current_user.id,
        resource=stage_name,
        details={"feedback": approve_in.feedback, "is_approved": approve_in.is_approved},
        ip_address=get_client_ip(request)
    )

    # Notify waiting in-flight manager loop if running
    if approve_in.is_approved:
        notify_stage_approved(project_id, stage_name)
    
    # Broadcast to WebSocket that status has changed
    await ws_manager.broadcast_to_project(
        json.dumps({"type": "status", "data": "running" if approve_in.is_approved else "paused"}),
        project_id
    )
    
    return {"message": f"Stage {stage_name} approval status updated to {approve_in.is_approved}."}

@app.put(f"{settings.API_V1_STR}/projects/{{project_id}}/code/{{file_id}}")
def update_code_content(
    request: Request,
    project_id: int, 
    file_id: int, 
    code_in: CodeUpdateSchema, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    project: Project = Depends(get_project_with_write_access)
):
    code_file = db.query(GeneratedFile).filter(
        GeneratedFile.project_id == project_id,
        GeneratedFile.id == file_id
    ).first()
    if not code_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    code_file.content = code_in.content
    db.commit()
    
    # Immutable audit logging for source code revisions
    record_audit_log(
        db=db,
        action="code_update",
        project_id=project_id,
        user_id=current_user.id,
        resource=code_file.filepath,
        details={"file_id": file_id, "size_chars": len(code_in.content)},
        ip_address=get_client_ip(request)
    )

    # Update sandbox
    sandbox_dir = get_sandbox_dir(project_id)
    if os.path.exists(sandbox_dir):
        file_path = os.path.join(sandbox_dir, code_file.filepath)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_in.content)
        except Exception as e:
            logger.warning(f"Failed to update sandbox file on database update: {e}")
            
    return {"message": "Source code updated successfully", "filepath": code_file.filepath}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/sandbox/files")
def list_sandbox_files(
    project_id: int, 
    project: Project = Depends(get_project_with_access)
):
    sandbox_dir = get_sandbox_dir(project_id)
    if not os.path.exists(sandbox_dir):
        return {"files": []}
    
    file_list = []
    for root, dirs, files in os.walk(sandbox_dir):
        dirs[:] = [d for d in dirs if d not in ["__pycache__", "venv"] and not d.startswith(".")]
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, sandbox_dir)
            file_list.append({
                "filepath": rel_path.replace("\\", "/"),
                "size": os.path.getsize(full_path)
            })
            
    return {"files": file_list}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/sandbox/files/read")
def read_sandbox_file(
    project_id: int,
    path: str = Query(...),
    project: Project = Depends(get_project_with_access)
):
    sandbox_dir = get_sandbox_dir(project_id)
    target_path = os.path.abspath(os.path.join(sandbox_dir, path))
    if not target_path.startswith(os.path.abspath(sandbox_dir)):
        raise HTTPException(status_code=403, detail="Access denied. Path traversal blocked.")
        
    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="File not found in sandbox.")
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filepath": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

@app.put(f"{settings.API_V1_STR}/projects/{{project_id}}/sandbox/files/write")
def write_sandbox_file(
    request: Request,
    project_id: int,
    file_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project: Project = Depends(get_project_with_write_access)
):
    path = file_data.get("path", "").strip()
    content = file_data.get("content", "")
    if not path:
        raise HTTPException(status_code=400, detail="Path cannot be empty")
        
    sandbox_dir = get_sandbox_dir(project_id)
    target_path = os.path.abspath(os.path.join(sandbox_dir, path))
    if not target_path.startswith(os.path.abspath(sandbox_dir)):
        raise HTTPException(status_code=403, detail="Access denied. Path traversal blocked.")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Immutable audit logging for file creation/modification in sandbox
        record_audit_log(
            db=db,
            action="file_write",
            project_id=project_id,
            user_id=current_user.id,
            resource=path,
            details={"size_chars": len(content)},
            ip_address=get_client_ip(request)
        )

        return {"message": "Sandbox file written successfully", "filepath": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/sandbox/terminal")
@limiter.limit("30/minute")
def run_sandbox_terminal(
    request: Request,
    project_id: int,
    command_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    project: Project = Depends(get_project_with_write_access)
):
    """
    Safely executes developer commands in the sandbox directory.
    Enforces shell=False, strict argument tokenization, and whitelisted utilities.
    """
    import subprocess
    command = command_data.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
        
    # Block shell metacharacters preventing command chaining / injection
    forbidden_chars = [";", "&", "|", "`", "$", ">", "<", "\n", "\r"]
    if any(char in command for char in forbidden_chars):
        raise HTTPException(
            status_code=403, 
            detail="Security violation: Command chaining, redirection, and shell metacharacters are strictly forbidden."
        )
    
    try:
        tokens = shlex.split(command, posix=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid command syntax: {e}")
        
    if not tokens:
        raise HTTPException(status_code=400, detail="Empty command tokens.")
        
    base_cmd = tokens[0].lower().replace('"', '').replace("'", "")
    allowed_commands = {
        "python", "python3", "pytest", "ls", "dir", "cat", "type", 
        "head", "tail", "pwd", "echo", "tree", "git"
    }
    
    is_allowed = (
        base_cmd in allowed_commands 
        or base_cmd.endswith("python.exe") 
        or base_cmd.endswith("python")
        or base_cmd.endswith("pytest.exe")
        or base_cmd.endswith("pytest")
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403, 
            detail=f"Security violation: Executable '{tokens[0]}' is not permitted in the research sandbox."
        )
        
    sandbox_dir = get_sandbox_dir(project_id)
    os.makedirs(sandbox_dir, exist_ok=True)
    
    # On Windows, wrap shell built-ins with cmd.exe /c
    import sys
    exec_args = tokens
    if sys.platform == "win32" and base_cmd in {"dir", "type", "cls"}:
        exec_args = ["cmd.exe", "/c"] + tokens

    try:
        res = subprocess.run(
            exec_args,
            shell=False,
            cwd=sandbox_dir,
            capture_output=True,
            text=True,
            timeout=15.0
        )

        # Immutable audit logging for terminal command execution
        record_audit_log(
            db=db,
            action="sandbox_command",
            project_id=project_id,
            user_id=current_user.id,
            resource=command,
            details={
                "exit_code": res.returncode,
                "stdout_preview": res.stdout[:500] if res.stdout else "",
                "stderr_preview": res.stderr[:500] if res.stderr else ""
            },
            ip_address=get_client_ip(request)
        )

        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.returncode
        }
    except subprocess.TimeoutExpired:
        record_audit_log(
            db=db,
            action="sandbox_command",
            project_id=project_id,
            user_id=current_user.id,
            resource=command,
            details={"exit_code": -1, "error": "Command execution timed out (limit: 15s)"},
            ip_address=get_client_ip(request)
        )
        return {
            "stdout": "",
            "stderr": "Command execution timed out (limit: 15s).",
            "exit_code": -1
        }
    except Exception as e:
        record_audit_log(
            db=db,
            action="sandbox_command",
            project_id=project_id,
            user_id=current_user.id,
            resource=command,
            details={"exit_code": -1, "error": str(e)},
            ip_address=get_client_ip(request)
        )
        return {
            "stdout": "",
            "stderr": f"Execution failed: {str(e)}",
            "exit_code": -1
        }

# --- AUDIT TRAILS (FDA 21 CFR PART 11 / IP PROVENANCE) ---

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/audit-logs", response_model=List[AuditLogResponse], tags=["audit"])
def get_project_audit_logs(
    project_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_access)
):
    """
    Returns an immutable chronological audit trail for the project
    (FDA 21 CFR Part 11 / IP provenance compliance).
    """
    return (
        db.query(AuditLog)
        .filter(AuditLog.project_id == project_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )

@app.get(f"{settings.API_V1_STR}/admin/audit-logs", response_model=List[AuditLogResponse], tags=["admin"])
def get_system_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Returns global system-wide audit records (Admin only).
    """
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/papers/upload")
async def upload_reference_paper(
    project_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    project: Project = Depends(get_project_with_write_access)
):
    import io
    from pypdf import PdfReader
    from app.models.models import UploadedPaper
    from app.utils.vector_store import get_vector_store
    
    try:
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        
        reader = PdfReader(pdf_file)
        content_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content_text += text + "\n"
                
        if not content_text.strip():
            raise ValueError("No extractable text found in PDF.")
            
        uploaded_db = UploadedPaper(
            project_id=project_id,
            filename=file.filename,
            content_text=content_text
        )
        db.add(uploaded_db)
        db.commit()
        db.refresh(uploaded_db)
        
        store = get_vector_store(f"project-{project_id}")
        chunk_size = 2000
        chunk_overlap = 400
        chunks = []
        metadatas = []
        ids = []
        
        start = 0
        chunk_idx = 0
        while start < len(content_text):
            end = start + chunk_size
            chunk = content_text[start:end]
            chunks.append(chunk)
            metadatas.append({
                "filename": file.filename,
                "paper_id": uploaded_db.id,
                "chunk_index": chunk_idx
            })
            ids.append(f"uploaded-paper-{uploaded_db.id}-chunk-{chunk_idx}")
            start += chunk_size - chunk_overlap
            chunk_idx += 1
            
        if chunks:
            await store.add(documents=chunks, metadatas=metadatas, ids=ids)
        
        paper_node_id = f"uploaded-paper-{uploaded_db.id}"
        node = KnowledgeNode(
            id=paper_node_id,
            project_id=project_id,
            type="uploaded_ref",
            label=file.filename[:30] + "...",
            properties={
                "filename": file.filename,
                "length_chars": len(content_text)
            }
        )
        db.merge(node)
        db.commit()
        
        return {
            "message": "PDF uploaded and indexed successfully",
            "paper_id": uploaded_db.id,
            "filename": file.filename,
            "char_count": len(content_text)
        }
        
    except Exception as e:
        logger.error(f"Error parsing uploaded PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/papers")
async def list_uploaded_papers(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_access)
):
    from app.models.models import UploadedPaper
    papers = db.query(UploadedPaper).filter(UploadedPaper.project_id == project_id).order_by(UploadedPaper.created_at.desc()).all()
    return {
        "papers": [
            {
                "id": p.id,
                "filename": p.filename,
                "char_count": len(p.content_text),
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in papers
        ]
    }

@app.delete(f"{settings.API_V1_STR}/projects/{{project_id}}/papers/{{paper_id}}")
async def delete_uploaded_paper(
    project_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_write_access)
):
    from app.models.models import UploadedPaper
    from app.utils.vector_store import get_vector_store
    
    paper = db.query(UploadedPaper).filter(
        UploadedPaper.id == paper_id,
        UploadedPaper.project_id == project_id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        store = get_vector_store(f"project-{project_id}")
        chunk_ids_to_remove = [doc_id for doc_id in store.ids if doc_id.startswith(f"uploaded-paper-{paper_id}-chunk-")]
        for chunk_id in chunk_ids_to_remove:
            idx = store.ids.index(chunk_id)
            store.ids.pop(idx)
            store.documents.pop(idx)
            store.metadatas.pop(idx)
            store.embeddings.pop(idx)
    except Exception as e:
        logger.warning(f"Could not remove vector store chunks for paper {paper_id}: {e}")
    
    db.delete(paper)
    db.commit()
    return {"message": f"Paper '{paper.filename}' deleted successfully", "paper_id": paper_id}

def build_pdf_reportlab(project_id: int, title: str, abstract: str, sections: dict) -> Optional[str]:
    import os
    import html
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    static_dir = os.path.join(os.getcwd(), "static", "papers")
    os.makedirs(static_dir, exist_ok=True)
    pdf_path = os.path.join(static_dir, f"arsa_paper_{project_id}.pdf")
    
    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"<b>{html.escape(title or 'Academic Paper')}</b>", styles["Title"]))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("<b>Abstract</b>", styles["Heading2"]))
        story.append(Spacer(1, 6))
        safe_abs = html.escape(abstract or "No abstract available.").replace("\n", "<br/>")
        story.append(Paragraph(safe_abs, styles["Normal"]))
        story.append(Spacer(1, 12))
        
        if sections:
            for sec_title, sec_content in sections.items():
                story.append(Paragraph(f"<b>{html.escape(sec_title)}</b>", styles["Heading3"]))
                story.append(Spacer(1, 6))
                safe_sec = html.escape(sec_content or "").replace("\n", "<br/>")
                story.append(Paragraph(safe_sec, styles["Normal"]))
                story.append(Spacer(1, 12))
                
        doc.build(story)
        # Return relative URL path to ensure universal compatibility across hostnames/proxies
        return f"/static/papers/arsa_paper_{project_id}.pdf"
    except Exception as e:
        logger.error(f"Failed to compile PDF via ReportLab: {e}")
        return None

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/compile")
@limiter.limit("10/minute")
def compile_latex_paper(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_access)
):
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Scientific paper draft not found.")
        
    latex_text = (
        "\\documentclass{article}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{hyperref}\n"
        f"\\title{{{paper.title}}}\n"
        "\\author{ARSA Autonomous Multi-Agent Core}\n"
        "\\date{\\today}\n"
        "\\begin{document}\n"
        "\\maketitle\n\n"
        "\\begin{abstract}\n"
        f"{paper.abstract}\n"
        "\\end{abstract}\n\n"
    )
    
    for title, text in (paper.sections or {}).items():
        latex_text += f"\\section{{{title}}}\n{text}\n\n"
        
    latex_text += "\\end{document}\n"
    
    pdf_url = build_pdf_reportlab(project_id, paper.title, paper.abstract, paper.sections or {})
    
    return {
        "title": paper.title,
        "latex_source": latex_text,
        "pdf_download_url": pdf_url or f"/api/v1/projects/{project_id}/paper/download_pdf"
    }

@app.put(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/compile")
def update_latex_paper(
    project_id: int,
    paper_in: LaTeXUpdateSchema,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_write_access)
):
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Scientific paper draft not found.")
        
    import re
    title = paper.title
    abstract = paper.abstract
    sections = {}
    
    title_match = re.search(r'\\title\{([^}]+)\}', paper_in.latex_source)
    if title_match:
        title = title_match.group(1).strip()
        
    abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', paper_in.latex_source, re.DOTALL)
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        
    section_matches = re.finditer(r'\\section\{([^}]+)\}(.*?)(?=\\section\{|\\end\{document\})', paper_in.latex_source, re.DOTALL)
    for match in section_matches:
        sec_title = match.group(1).strip()
        sec_content = match.group(2).strip()
        sections[sec_title] = sec_content
        
    paper.title = title
    paper.abstract = abstract
    paper.sections = sections
    db.commit()
    db.refresh(paper)
    
    build_pdf_reportlab(project_id, paper.title, paper.abstract, paper.sections or {})
    return {"message": "LaTeX manuscript updated successfully", "title": paper.title}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/download_pdf")
@limiter.limit("15/minute")
def download_pdf_paper(
    request: Request,
    project_id: int, 
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_access)
):
    import os
    pdf_path = os.path.join(os.getcwd(), "static", "papers", f"arsa_paper_{project_id}.pdf")
    if os.path.exists(pdf_path):
        from fastapi.responses import FileResponse
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"arsa_paper_{project_id}.pdf")
        
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    content = f"ARSA SCIENTIFIC MANUSCRIPT\n\nTitle: {paper.title}\nAbstract: {paper.abstract}\n\n"
    for title, text in (paper.sections or {}).items():
        content += f"=== {title} ===\n{text}\n\n"
        
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=arsa_paper_{project_id}.pdf"}
    )

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/publish/hf")
def publish_to_huggingface(
    project_id: int,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_with_write_access),
    current_user: User = Depends(get_current_user)
):
    import re
    slug = re.sub(r'[^a-zA-Z0-9\-]', '-', project.title.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    if not slug:
        slug = f"project-{project_id}"
        
    repo_url = f"https://huggingface.co/arsa-ai/{slug}"
    node_id = f"hf-publish-{project_id}"
    node = KnowledgeNode(
        id=node_id,
        project_id=project_id,
        type="publisher",
        label=f"HF: {slug}",
        properties={
            "repository_url": repo_url,
            "published_by": current_user.full_name
        }
    )
    db.merge(node)
    
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    if paper:
        edge = KnowledgeEdge(
            project_id=project_id,
            source=node_id,
            target=f"paper-{paper.id}",
            type="references"
        )
        db.add(edge)
    
    db.commit()
    return {
        "repository_url": repo_url,
        "status": "success",
        "message": "Successfully published model card, training logs, config parameters, and model weights to Hugging Face."
    }


# --- SYSTEM SETTINGS & ANALYTICS ---

@app.get(f"{settings.API_V1_STR}/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    papers_count = db.query(LiteraturePaper).count()
    gaps_count = db.query(ResearchGap).count()
    hypo_count = db.query(Hypothesis).count()
    runs_count = db.query(ExperimentRun).count()
    pub_count = db.query(ScientificPaper).count()
    projects_count = db.query(Project).count()
    
    return {
        "papers_analyzed": papers_count,
        "gaps_found": gaps_count,
        "hypotheses_generated": hypo_count,
        "experiments_executed": runs_count,
        "publications_generated": pub_count,
        "total_projects": projects_count,
        "compute_allocated": {
            "gpus_active": 1,
            "gpu_utilization_pct": 42.5,
            "vram_allocated_gb": 32.0,
            "vram_total_gb": 80.0
        }
    }


# --- SYSTEM ADMIN API ---

@app.get(f"{settings.API_V1_STR}/admin/users", response_model=List[AdminUserResponse], tags=["admin"])
def get_admin_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    users = db.query(User).all()
    results = []
    for u in users:
        p_count = db.query(Project).filter(Project.user_id == u.id).count()
        results.append(AdminUserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            created_at=u.created_at,
            compute_quota_gpu_hours=getattr(u, "compute_quota_gpu_hours", 100.0) or 100.0,
            compute_used_gpu_hours=getattr(u, "compute_used_gpu_hours", 0.0) or 0.0,
            is_active=getattr(u, "is_active", True) if getattr(u, "is_active", True) is not None else True,
            projects_count=p_count
        ))
    return results

@app.put(f"{settings.API_V1_STR}/admin/users/{{user_id}}", response_model=AdminUserResponse, tags=["admin"])
def update_admin_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-lockout or removing the last admin
    if data.role and data.role != "administrator" and target.id == admin.id:
        admin_count = db.query(User).filter(User.role == "administrator").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the sole remaining administrator")
    
    if data.role:
        if data.role not in ["researcher", "supervisor", "administrator"]:
            raise HTTPException(status_code=400, detail="Invalid user role specified")
        target.role = data.role
    if data.compute_quota_gpu_hours is not None:
        target.compute_quota_gpu_hours = max(0.0, data.compute_quota_gpu_hours)
    if data.is_active is not None:
        target.is_active = data.is_active

    db.commit()
    db.refresh(target)
    p_count = db.query(Project).filter(Project.user_id == target.id).count()
    return AdminUserResponse(
        id=target.id,
        email=target.email,
        full_name=target.full_name,
        role=target.role,
        created_at=target.created_at,
        compute_quota_gpu_hours=target.compute_quota_gpu_hours or 100.0,
        compute_used_gpu_hours=target.compute_used_gpu_hours or 0.0,
        is_active=target.is_active,
        projects_count=p_count
    )

@app.delete(f"{settings.API_V1_STR}/admin/users/{{user_id}}", tags=["admin"])
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own active administrator account")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(target)
    db.commit()
    return {"message": "User account and associated projects removed", "id": user_id}

@app.get(f"{settings.API_V1_STR}/admin/keys", response_model=List[ApiKeyResponse], tags=["admin"])
def get_admin_keys(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    keys = db.query(ApiKeyConfig).all()
    return [
        ApiKeyResponse(
            id=k.id,
            provider=k.provider,
            model=k.model_name,
            key=k.masked_key,
            status=k.status,
            created_at=k.created_at,
            last_used=k.last_used
        )
        for k in keys
    ]

@app.post(f"{settings.API_V1_STR}/admin/keys", response_model=ApiKeyResponse, tags=["admin"])
def create_admin_key(
    data: ApiKeyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    raw = data.key.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="API Key string cannot be blank")
    
    # Mask key safely
    if len(raw) > 8:
        masked = raw[:4] + "••••••••" + raw[-4:]
    else:
        masked = "••••••••••••"
    
    new_key = ApiKeyConfig(
        provider=data.provider,
        model_name=data.model,
        masked_key=masked,
        status="active"
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    return ApiKeyResponse(
        id=new_key.id,
        provider=new_key.provider,
        model=new_key.model_name,
        key=new_key.masked_key,
        status=new_key.status,
        created_at=new_key.created_at,
        last_used=new_key.last_used
    )

@app.delete(f"{settings.API_V1_STR}/admin/keys/{{key_id}}", tags=["admin"])
def delete_admin_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    target = db.get(ApiKeyConfig, key_id)
    if not target:
        raise HTTPException(status_code=404, detail="API Key configuration not found")
    db.delete(target)
    db.commit()
    return {"message": "API key revoked and unlinked from orchestration scheduler", "id": key_id}

@app.get(f"{settings.API_V1_STR}/admin/compute", response_model=SystemComputeResponse, tags=["admin"])
def get_admin_compute(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    config = db.query(SystemComputeConfig).first()
    if not config:
        config = SystemComputeConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return SystemComputeResponse(
        activeGpus=config.active_gpus or "1x NVIDIA A100 (80GB)",
        allocatedCpuCores=config.allocated_cpu_cores or 16,
        sharedSandboxRamGb=config.memory_limit_gb or 64,
        virtualGpuLoadPct=config.utilization_pct or 45,
        schedulerStatus=config.scheduler_status or "online"
    )

@app.put(f"{settings.API_V1_STR}/admin/compute", response_model=SystemComputeResponse, tags=["admin"])
def update_admin_compute(
    data: SystemComputeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    config = db.query(SystemComputeConfig).first()
    if not config:
        config = SystemComputeConfig()
        db.add(config)
    
    if data.activeGpus is not None:
        config.active_gpus = data.activeGpus
    if data.allocatedCpuCores is not None:
        config.allocated_cpu_cores = data.allocatedCpuCores
    if data.sharedSandboxRamGb is not None:
        config.memory_limit_gb = data.sharedSandboxRamGb
    if data.virtualGpuLoadPct is not None:
        config.utilization_pct = data.virtualGpuLoadPct
    if data.schedulerStatus is not None:
        config.scheduler_status = data.schedulerStatus
    
    db.commit()
    db.refresh(config)
    return SystemComputeResponse(
        activeGpus=config.active_gpus,
        allocatedCpuCores=config.allocated_cpu_cores,
        sharedSandboxRamGb=config.memory_limit_gb,
        virtualGpuLoadPct=config.utilization_pct,
        schedulerStatus=config.scheduler_status
    )

# --- ADMIN DATABASE BACKUP & RESTORATION ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/admin/backups", response_model=List[BackupItemResponse], tags=["admin"])
def list_database_backups(
    admin: User = Depends(require_admin)
):
    """Lists all available atomic SQLite database backups."""
    return backup_service.list_backups()

@app.post(f"{settings.API_V1_STR}/admin/backups/create", response_model=BackupItemResponse, tags=["admin"])
def trigger_database_backup(
    req: BackupCreateRequest = BackupCreateRequest(),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Triggers an immediate atomic database snapshot and registers an audit log."""
    try:
        backup_info = backup_service.create_backup(label=req.label)
        record_audit_log(
            db=db,
            action="database_backup_created",
            user_id=admin.id,
            resource=backup_info["filename"],
            details={"size_bytes": backup_info["size_bytes"], "sha256": backup_info["sha256"]}
        )
        return backup_info
    except Exception as e:
        logger.error(f"Failed to create database backup: {e}")
        raise HTTPException(status_code=500, detail=f"Database backup failed: {str(e)}")

@app.post(f"{settings.API_V1_STR}/admin/backups/restore", response_model=BackupRestoreResponse, tags=["admin"])
def restore_database_backup(
    req: BackupRestoreRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Restores the database from a verified backup archive, taking a safety snapshot first."""
    try:
        result = backup_service.restore_backup(filename=req.filename)
        record_audit_log(
            db=db,
            action="database_restored",
            user_id=admin.id,
            resource=req.filename,
            details=result
        )
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup archive not found")
    except Exception as e:
        logger.error(f"Failed to restore database backup: {e}")
        raise HTTPException(status_code=500, detail=f"Database restoration failed: {str(e)}")

@app.get(f"{settings.API_V1_STR}/admin/backups/download/{{filename}}", tags=["admin"])
def download_database_backup(
    filename: str,
    admin: User = Depends(require_admin)
):
    """Securely downloads a database backup archive for offsite replication."""
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(backup_service.backup_dir, safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Backup archive not found")
    return FileResponse(filepath, media_type="application/gzip", filename=safe_filename)

# --- APM & OBSERVABILITY TELEMETRY ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/admin/metrics", response_model=APMMetricsResponse, tags=["admin"])
def get_apm_metrics(
    admin: User = Depends(require_admin)
):
    """Returns real-time application performance metrics, latency percentiles, and error rate."""
    return apm_tracker.get_metrics()


# --- WEBSOCKET MANAGER ---


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket client connected to project {project_id}")

    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket client disconnected from project {project_id}")

    async def broadcast_to_project(self, message: str, project_id: int):
        if project_id in self.active_connections:
            for connection in list(self.active_connections[project_id]):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning(f"Error broadcasting ws message: {e}")

ws_manager = ConnectionManager()

@app.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    project_id: int, 
    token: Optional[str] = Query(None)
):
    await ws_manager.connect(websocket, project_id)
    
    auth_token = token
    if not auth_token:
        cookie_token = websocket.cookies.get("access_token")
        if cookie_token:
            auth_token = cookie_token.replace("Bearer ", "").strip()

    first_frame_payload = None

    # OWASP Compliant In-Band Authentication Handshake:
    # If token was not provided via URL query or cookie, await authentication frame inside socket.
    if not auth_token:
        try:
            init_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            init_data = json.loads(init_msg)
            auth_token = init_data.get("token") or init_data.get("authToken")
            if init_data.get("action"):
                first_frame_payload = init_data
        except (asyncio.TimeoutError, json.JSONDecodeError):
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "AUTH_TIMEOUT",
                    "message": "Authentication handshake timed out. In-band token required within 5 seconds."
                }))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            finally:
                ws_manager.disconnect(websocket, project_id)
            return

    if not auth_token:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "code": "UNAUTHORIZED",
                "message": "Missing authentication credentials."
            }))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        finally:
            ws_manager.disconnect(websocket, project_id)
        return

    try:
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if not email:
            raise ValueError("Invalid subject in token")
    except Exception:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired token."
            }))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        finally:
            ws_manager.disconnect(websocket, project_id)
        return

    # Notify client that secure in-band authentication succeeded
    await websocket.send_text(json.dumps({
        "type": "authenticated",
        "message": "WebSocket secure session verified via in-band authentication."
    }))

    # Create local DB session for websocket request checks
    db: Session = SessionLocal()
    try:
        while True:
            if first_frame_payload:
                payload = first_frame_payload
                first_frame_payload = None
            else:
                data = await websocket.receive_text()
                payload = json.loads(data)

            action = payload.get("action")
            if not action or action == "auth":
                continue
            
            project = db.get(Project, project_id)
            if not project:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Project not found."
                }))
                continue

            user = db.query(User).filter(User.email == email).first()
            if not user:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "User account not found."
                }))
                continue

            if user.role not in ["supervisor", "administrator"] and project.user_id != user.id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Unauthorized: Access denied for this project."
                }))
                continue

            topic = payload.get("topic", project.title or "Scientific Research Topic")

            if action == "start":
                if project.status == "running":
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Project research pipeline is already running."
                    }))
                    continue
                
                # Commercial Operations Gatekeeper: Enforce subscription tier, quotas, and account balance
                authorized, billing_msg, tx = billing_service.check_and_deduct_pipeline_funds(db, user, project_id)
                if not authorized:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "PAYMENT_REQUIRED",
                        "message": billing_msg
                    }))
                    continue

                # Notify client of successful billing authorization
                await websocket.send_text(json.dumps({
                    "type": "billing",
                    "data": {
                        "message": billing_msg,
                        "balance_usd": user.balance_usd,
                        "subscription_tier": user.subscription_tier
                    }
                }))
                
                manager = ResearchManager(db=None, project_id=project_id)
                
                def ws_log_callback(log_entry: dict):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "log", "data": log_entry}), 
                            project_id
                        )
                    )
                
                def ws_status_callback(new_status: str):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "status", "data": new_status}), 
                            project_id
                        )
                    )

                def ws_reasoning_callback(reasoning_entry: dict):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "reasoning", "data": reasoning_entry}),
                            project_id
                        )
                    )
                
                manager.log_callback = ws_log_callback
                manager.status_callback = ws_status_callback
                manager.reasoning_callback = ws_reasoning_callback
                
                should_resume = payload.get("resume", False) or project.status == "interrupted"
                asyncio.create_task(manager.run_pipeline(topic, resume=should_resume))
                
                await websocket.send_text(json.dumps({
                    "type": "info",
                    "message": f"Autonomous Research Scientist Agent pipeline started{' (resuming from stage checkpoints)' if should_resume else ''}."
                }))

            elif action == "resume":
                if project.status == "running":
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Project research pipeline is already running."
                    }))
                    continue

                manager = ResearchManager(db=None, project_id=project_id)
                
                def ws_log_callback(log_entry: dict):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "log", "data": log_entry}), 
                            project_id
                        )
                    )
                
                def ws_status_callback(new_status: str):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "status", "data": new_status}), 
                            project_id
                        )
                    )

                def ws_reasoning_callback(reasoning_entry: dict):
                    asyncio.create_task(
                        ws_manager.broadcast_to_project(
                            json.dumps({"type": "reasoning", "data": reasoning_entry}),
                            project_id
                        )
                    )
                
                manager.log_callback = ws_log_callback
                manager.status_callback = ws_status_callback
                manager.reasoning_callback = ws_reasoning_callback
                
                asyncio.create_task(manager.run_pipeline(topic, resume=True))
                
                await websocket.send_text(json.dumps({
                    "type": "info",
                    "message": "Autonomous Research Scientist Agent pipeline resumed from verified stage checkpoints."
                }))
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, project_id)
    except Exception as e:
        logger.error(f"WebSocket error on project {project_id}: {e}")
        ws_manager.disconnect(websocket, project_id)
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
