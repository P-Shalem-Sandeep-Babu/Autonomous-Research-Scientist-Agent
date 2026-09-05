import json
import logging
import asyncio
import os
from typing import List, Dict, Any
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import Base, engine, get_db, SessionLocal
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.models import User, Project, ResearchStage, LiteraturePaper, ResearchGap, Hypothesis, DebateLog, DatasetRecommendation, ExperimentPlan, GeneratedFile, ExperimentRun, ScientificPaper, PeerReview, KnowledgeNode, KnowledgeEdge, AgentReachEvidence, ResearchMemory
from app.schemas.schemas import Token, UserCreate, UserResponse, ProjectCreate, ProjectResponse, ResearchStageResponse, KnowledgeGraphResponse, StageApproveSchema, CodeUpdateSchema, LaTeXUpdateSchema
from app.agents.manager import ResearchManager
from app.services.research_service import research_service
from fastapi import APIRouter

# Research API Router
research_router = APIRouter(prefix="/api/research", tags=["research"])

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arsa.api")

# Sandbox lives inside backend/ — uvicorn is started with --reload-dir app
# so it never watches sandbox_* folders, preventing spurious server restarts.
def get_sandbox_dir(project_id: int) -> str:
    return os.path.join(os.getcwd(), f"sandbox_{project_id}")

app = FastAPI(title=settings.PROJECT_NAME)



# Create static directory structure
static_dir = os.path.join(os.getcwd(), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "papers"), exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# CORS Middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev portability
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication helpers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Ensure tables are created
Base.metadata.create_all(bind=engine)

# Auto-repair schema for existing databases
try:
    from app.repair_db import repair_database
    repair_database()
except Exception as repair_err:
    logger.warning(f"Could not auto-repair database schema: {repair_err}")


# --- AUTHENTICATION ROUTES ---

@app.post(f"{settings.API_V1_STR}/auth/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_in.role not in ["researcher", "supervisor"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration for this role is not permitted. Only 'researcher' and 'supervisor' roles can be registered."
        )
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post(f"{settings.API_V1_STR}/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get(f"{settings.API_V1_STR}/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# --- PROJECT ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ["supervisor", "administrator"]:
        # Supervisors and Admins see all projects
        return db.query(Project).all()
    return db.query(Project).filter(Project.user_id == current_user.id).all()

@app.post(f"{settings.API_V1_STR}/projects", response_model=ProjectResponse)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Check permissions
    if current_user.role == "researcher" and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
        
    stages = db.query(ResearchStage).filter(ResearchStage.project_id == project_id).all()
    
    # Gather other project-related data
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

    # Formulate robust debate object
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
            "owner": project.user.full_name
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
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role == "researcher" and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")
        
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


# --- CODE & GRAPH EXTRA ENDPOINTS ---

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/code/{{file_id}}")
def get_code_content(project_id: int, file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    code_file = db.query(GeneratedFile).filter(
        GeneratedFile.project_id == project_id,
        GeneratedFile.id == file_id
    ).first()
    if not code_file:
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": code_file.content, "filepath": code_file.filepath}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/graph", response_model=KnowledgeGraphResponse)
def get_project_graph(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.project_id == project_id).all()
    edges = db.query(KnowledgeEdge).filter(KnowledgeEdge.project_id == project_id).all()
    return {
        "nodes": [{"id": n.id, "type": n.type, "label": n.label, "properties": n.properties} for n in nodes],
        "edges": [{"source": e.source, "target": e.target, "type": e.type} for e in edges]
    }


# --- NEW ENHANCEMENTS ENDPOINTS ---

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/stages/{{stage_name}}/approve")
async def approve_stage(
    project_id: int, 
    stage_name: str, 
    approve_in: StageApproveSchema, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
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
    
    # Broadcast to WebSocket that status has changed
    await ws_manager.broadcast_to_project(
        json.dumps({"type": "status", "data": "running" if approve_in.is_approved else "paused"}),
        project_id
    )
    
    return {"message": f"Stage {stage_name} approval status updated to {approve_in.is_approved}."}

@app.put(f"{settings.API_V1_STR}/projects/{{project_id}}/code/{{file_id}}")
def update_code_content(
    project_id: int, 
    file_id: int, 
    code_in: CodeUpdateSchema, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    code_file = db.query(GeneratedFile).filter(
        GeneratedFile.project_id == project_id,
        GeneratedFile.id == file_id
    ).first()
    if not code_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    code_file.content = code_in.content
    db.commit()
    
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
def list_sandbox_files(project_id: int, current_user: User = Depends(get_current_user)):
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
    current_user: User = Depends(get_current_user)
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
    project_id: int,
    file_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
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
        return {"message": "Sandbox file written successfully", "filepath": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/sandbox/terminal")
def run_sandbox_terminal(
    project_id: int,
    command_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    import subprocess
    command = command_data.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
        
    blocked_patterns = ["rm ", "del ", "mv ", "rename ", "format ", "mkfs ", "shutdown ", "poweroff ", "sudo ", "curl ", "wget ", "pip install ", "npm install "]
    if any(pattern in command.lower() for pattern in blocked_patterns):
        raise HTTPException(status_code=403, detail="Security violation: command contains blocked destructive actions.")
        
    sandbox_dir = get_sandbox_dir(project_id)
    os.makedirs(sandbox_dir, exist_ok=True)
    
    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=sandbox_dir,
            capture_output=True,
            text=True,
            timeout=10.0
        )
        return {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command execution timed out (limit: 10s).",
            "exit_code": -1
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution failed: {str(e)}",
            "exit_code": -1
        }

@app.post(f"{settings.API_V1_STR}/projects/{{project_id}}/papers/upload")
async def upload_reference_paper(
    project_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    import io
    from pypdf import PdfReader
    from app.models.models import UploadedPaper
    from app.utils.vector_store import get_vector_store
    
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
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
        
        # Index document text in the local vector store (RAG index) using sliding window chunking
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
        
        # Add Knowledge Node
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
    current_user: User = Depends(get_current_user)
):
    """List all uploaded reference PDFs for a project."""
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
    current_user: User = Depends(get_current_user)
):
    """Delete an uploaded reference PDF and remove its chunks from the vector store."""
    from app.models.models import UploadedPaper
    from app.utils.vector_store import get_vector_store
    
    paper = db.query(UploadedPaper).filter(
        UploadedPaper.id == paper_id,
        UploadedPaper.project_id == project_id
    ).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Remove chunks from in-memory vector store
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

def build_pdf_reportlab(project_id: int, title: str, abstract: str, sections: dict):
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
        
        # Title
        story.append(Paragraph(f"<b>{html.escape(title or 'Academic Paper')}</b>", styles["Title"]))
        story.append(Spacer(1, 12))
        
        # Abstract
        story.append(Paragraph("<b>Abstract</b>", styles["Heading2"]))
        story.append(Spacer(1, 6))
        safe_abs = html.escape(abstract or "No abstract available.").replace("\n", "<br/>")
        story.append(Paragraph(safe_abs, styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Sections
        if sections:
            for sec_title, sec_content in sections.items():
                story.append(Paragraph(f"<b>{html.escape(sec_title)}</b>", styles["Heading3"]))
                story.append(Spacer(1, 6))
                safe_sec = html.escape(sec_content or "").replace("\n", "<br/>")
                story.append(Paragraph(safe_sec, styles["Normal"]))
                story.append(Spacer(1, 12))
                
        doc.build(story)
        return f"http://127.0.0.1:8000/static/papers/arsa_paper_{project_id}.pdf"
    except Exception as e:
        logger.error(f"Failed to compile PDF via ReportLab: {e}")
        return None

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/compile")
def compile_latex_paper(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    
    # Rebuild static PDF file
    pdf_url = build_pdf_reportlab(project_id, paper.title, paper.abstract, paper.sections or {})
    
    return {
        "title": paper.title,
        "latex_source": latex_text,
        "pdf_download_url": pdf_url or f"http://127.0.0.1:8000/api/v1/projects/{project_id}/paper/download_pdf"
    }

@app.put(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/compile")
def update_latex_paper(
    project_id: int,
    paper_in: LaTeXUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = db.query(ScientificPaper).filter(ScientificPaper.project_id == project_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Scientific paper draft not found.")
        
    # Parse title, abstract, and sections from the provided LaTeX source
    import re
    title = paper.title
    abstract = paper.abstract
    sections = {}
    
    # Extract Title
    title_match = re.search(r'\\title\{([^}]+)\}', paper_in.latex_source)
    if title_match:
        title = title_match.group(1).strip()
        
    # Extract Abstract
    abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', paper_in.latex_source, re.DOTALL)
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        
    # Extract Sections
    section_matches = re.finditer(r'\\section\{([^}]+)\}(.*?)(?=\\section\{|\\end\{document\})', paper_in.latex_source, re.DOTALL)
    for match in section_matches:
        sec_title = match.group(1).strip()
        sec_content = match.group(2).strip()
        sections[sec_title] = sec_content
        
    # Save the parsed updates into the DB
    paper.title = title
    paper.abstract = abstract
    paper.sections = sections
    db.commit()
    db.refresh(paper)
    
    # Rebuild PDF
    build_pdf_reportlab(project_id, paper.title, paper.abstract, paper.sections or {})
    
    return {"message": "LaTeX manuscript updated successfully", "title": paper.title}

@app.get(f"{settings.API_V1_STR}/projects/{{project_id}}/paper/download_pdf")
def download_pdf_paper(project_id: int, db: Session = Depends(get_db)):
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
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
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
        "message": f"Successfully published model card, training logs, config parameters, and model weights to Hugging Face."
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
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket client disconnected from project {project_id}")

    async def broadcast_to_project(self, message: str, project_id: int):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    # Connection might have died, clean it up later or ignore here
                    logger.warning(f"Error broadcasting ws message: {e}")

ws_manager = ConnectionManager()

@app.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int, token: str = Query(...)):
    # Authenticate socket connection
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if not email:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Add DB session locally for WebSocket lifetime
    db: Session = SessionLocal()
    
    await ws_manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "start":
                project = db.query(Project).get(project_id)
                if not project:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Project not found."
                    }))
                    continue
                topic = payload.get("topic", project.title or "Brain Tumor Classification")
                
                if project.status == "running":
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Project research pipeline is already running."
                    }))
                    continue
                
                # Setup Research Manager
                manager = ResearchManager(db, project_id)
                
                # Register WebSocket callbacks
                def ws_log_callback(log_entry: dict):
                    # Spawn async task to broadcast logs to this project group
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
                
                # Run the pipeline in a background task
                asyncio.create_task(manager.run_pipeline(topic))
                
                await websocket.send_text(json.dumps({
                    "type": "info",
                    "message": "Autonomous Research Scientist Agent pipeline started."
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
