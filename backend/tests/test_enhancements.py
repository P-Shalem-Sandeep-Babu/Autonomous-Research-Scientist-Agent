import pytest
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.core.database import Base
from app.models.models import User, Project, ResearchStage, GeneratedFile

# Set up test database
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    # Seed a default researcher and get a token
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "tester@arsa.ai",
            "password": "password123",
            "full_name": "Test User",
            "role": "researcher"
        }
    )
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

def get_auth_headers():
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "tester@arsa.ai", "password": "password123"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_stage_approval_rest_api():
    headers = get_auth_headers()
    
    # 1. Create a project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "Sandbox Test Project", "description": "Analyzing HITL gates"},
        headers=headers
    )
    proj_id = proj_resp.json()["id"]

    # 2. Approve a stage (e.g. debate)
    approve_resp = client.post(
        f"/api/v1/projects/{proj_id}/stages/debate/approve",
        json={"is_approved": True, "feedback": "Excellent debate, proceed to planning"},
        headers=headers
    )
    assert approve_resp.status_code == 200
    assert "updated to True" in approve_resp.json()["message"]

def test_sandbox_code_updates_rest_api():
    headers = get_auth_headers()
    
    # 1. Create a project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "Code Sandbox Project", "description": "Editing training loops"},
        headers=headers
    )
    proj_id = proj_resp.json()["id"]
    
    # Add a dummy file record to update
    db = TestingSessionLocal()
    code_file = GeneratedFile(
        project_id=proj_id,
        filepath="config.yaml",
        content="epochs: 10\nlr: 1e-4",
        explanation="Default configurations"
    )
    db.add(code_file)
    db.commit()
    db.refresh(code_file)
    file_id = code_file.id
    db.close()

    # 2. Update code content
    update_resp = client.put(
        f"/api/v1/projects/{proj_id}/code/{file_id}",
        json={"content": "epochs: 50\nlr: 5e-5"},
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["message"] == "Source code updated successfully"

def test_pdf_parsing_upload_fail_on_empty():
    headers = get_auth_headers()
    
    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "PDF Upload Project", "description": "Parsing references"},
        headers=headers
    )
    proj_id = proj_resp.json()["id"]
    
    # Upload an empty mock text file posing as PDF (should raise parsing ValueError/400)
    fake_pdf = io.BytesIO(b"Hello World")
    files = {"file": ("reference.pdf", fake_pdf, "application/pdf")}
    
    upload_resp = client.post(
        f"/api/v1/projects/{proj_id}/papers/upload",
        files=files,
        headers=headers
    )
    # Since it's not a real PDF containing readable pages, the PDFReader will fail to extract text, triggering our 400 response
    assert upload_resp.status_code == 400
    assert "Failed to process PDF" in upload_resp.json()["detail"]
