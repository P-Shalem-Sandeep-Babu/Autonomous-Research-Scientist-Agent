import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.core.database import Base
from app.core.security import get_password_hash
from app.utils.arxiv import search_arxiv
from app.utils.vector_store import get_vector_store
from app.models.models import User, Project, ResearchStage, LiteraturePaper, ResearchGap, Hypothesis, DebateLog, DatasetRecommendation, ExperimentPlan, GeneratedFile, ExperimentRun, ScientificPaper, PeerReview, KnowledgeNode, KnowledgeEdge, AgentReachEvidence, ResearchMemory, UploadedPaper

# Set up test database
SQLALCHEMY_DATABASE_URL = "sqlite://"  # In-memory database

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database dependency in FastAPI app
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
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

def test_user_registration_and_login():
    # 1. Test Register
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test_researcher@arsa.ai",
            "password": "securepassword123",
            "full_name": "Test User",
            "role": "researcher"
        }
    )
    assert reg_response.status_code == 200
    data = reg_response.json()
    assert data["email"] == "test_researcher@arsa.ai"
    assert data["full_name"] == "Test User"

    # 2. Test Login
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test_researcher@arsa.ai",
            "password": "securepassword123"
        }
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_project_creation():
    # Register and login to get token
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "creator@arsa.ai",
            "password": "password123",
            "full_name": "Creator User",
            "role": "researcher"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "creator@arsa.ai", "password": "password123"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "Brain Tumor Research", "description": "Analyzing MRI scans"},
        headers=headers
    )
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    assert proj_data["title"] == "Brain Tumor Research"
    assert proj_data["status"] == "idle"

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_arxiv_parser():
    # Test that the arXiv API search runs and handles queries safely
    res = await search_arxiv("brain tumors", max_results=1)
    # The utility returns a list of dictionaries (or empty list if offline, but it should not crash)
    assert isinstance(res, list)
    if len(res) > 0:
        assert "title" in res[0]
        assert "abstract" in res[0]
        assert "url" in res[0]

@pytest.mark.anyio
async def test_custom_vector_store():
    # Test adding documents and querying custom vector store
    store = get_vector_store("test_collection")
    await store.add(
        documents=["Deep learning methods for brain tumor detection", "Genomic sequences of lower-grade gliomas"],
        metadatas=[{"topic": "mri"}, {"topic": "genomics"}],
        ids=["doc1", "doc2"]
    )
    
    res = await store.query("brain tumor", n_results=1)
    assert len(res["documents"]) == 1
    assert "brain tumor" in res["documents"][0].lower()
    assert res["metadatas"][0]["topic"] == "mri"

def test_websocket_connection():
    # Register and login to get token
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ws_user@arsa.ai",
            "password": "password123",
            "full_name": "WS User",
            "role": "researcher"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ws_user@arsa.ai", "password": "password123"}
    )
    token = login_resp.json()["access_token"]
    
    # Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "WS Project", "description": "Testing websockets"},
        headers={"Authorization": f"Bearer {token}"}
    )
    proj_id = proj_resp.json()["id"]
    
    # Connect to WebSocket
    with client.websocket_connect(f"/ws/projects/{proj_id}?token={token}") as websocket:
        assert websocket is not None

