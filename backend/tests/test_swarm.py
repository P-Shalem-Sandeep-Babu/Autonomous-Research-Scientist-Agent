import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_db
from app.core.database import Base
from app.models.models import Project, ResearchStage, ScientificPaper, PeerReview, ResearchMemory
from app.agents.manager import ResearchManager
from app.agents.debate import DebateAgent
from app.agents.memory import MemoryAgent

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

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_debate_personas():
    db = TestingSessionLocal()
    try:
        # Create a test project
        project = Project(title="AI Research on MRI", description="Debating personas", user_id=1, status="idle")
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Add a hypothesis
        from app.models.models import Hypothesis
        hypo = Hypothesis(project_id=project.id, statement="ViT is better than CNN", reasoning="Self-attention", confidence_level=0.9)
        db.add(hypo)
        db.commit()
        
        # Set up a research stage for debate
        stage = ResearchStage(project_id=project.id, stage_name="debate", status="pending")
        db.add(stage)
        db.commit()

        # Instantiate DebateAgent
        agent = DebateAgent(db, project.id)
        
        # Mock generate_text to return valid JSON
        mock_response = """{
            "proposal_a": "CNN model",
            "proposal_b": "ViT model",
            "proposal_c": "RL Hybrid",
            "debate_rounds": [
                {"agent": "Moderator", "message": "Let's debate."},
                {"agent": "Neuroscientist", "message": "Clinical borders match."},
                {"agent": "Hardware Optimizer", "message": "GFLOP count is small."},
                {"agent": "Statistician", "message": "Siemens scanners show bias."}
            ],
            "winner_proposal": "Proposal C",
            "rationale": "Better compute and clinical boundaries."
        }"""
        
        with patch("app.agents.debate.generate_text", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            res = await agent.execute()
            
            # Assertions
            assert res["winner_proposal"] == "Proposal C"
            assert len(res["debate_rounds"]) == 4
            agents_in_debate = [round["agent"] for round in res["debate_rounds"]]
            assert "Moderator" in agents_in_debate
            assert "Neuroscientist" in agents_in_debate
            assert "Hardware Optimizer" in agents_in_debate
            assert "Statistician" in agents_in_debate
    finally:
        db.close()

@pytest.mark.anyio
async def test_memory_global_store():
    db = TestingSessionLocal()
    try:
        project = Project(title="Global Memory Project", description="Testing cognitive memory store", user_id=1, status="idle")
        db.add(project)
        db.commit()
        db.refresh(project)
        
        stage = ResearchStage(project_id=project.id, stage_name="memory", status="pending")
        db.add(stage)
        db.commit()

        # Seed a literature paper to derive memories from
        from app.models.models import LiteraturePaper
        paper = LiteraturePaper(
            project_id=project.id,
            title="Domain-Adversarial Vision Transformer (DA-ViT) for MRI",
            methodology="We propose a Domain-Adversarial Vision Transformer that utilizes gradient reversal...",
            findings="The proposed DA-ViT achieved a statistically significant improvement...",
            limitations="However, scanner-related domain shifts and MRI background noise reduction remain a challenge for convergence.",
            relevance_score=9.5,
            source="local reference"
        )
        db.add(paper)
        db.commit()
        
        agent = MemoryAgent(db, project.id)
        
        # Execute Memory consolidation
        res = await agent.execute(findings={})
        assert res["memories_saved"] == 3
        
        # Query memory using retrieve_memories
        retrieved = await agent.retrieve_memories("gradient reversal")
        assert len(retrieved) > 0
        assert retrieved[0]["key"] == f"method_{project.id}_global_memory_project"
        
        # Query again with something not matching to hit database fallback
        retrieved_fallback = await agent.retrieve_memories("convergence")
        assert len(retrieved_fallback) > 0
        assert retrieved_fallback[0]["key"] == f"limitation_{project.id}_global_memory_project"
    finally:
        db.close()

@pytest.mark.anyio
@patch("app.agents.manager.LiteratureReviewAgent")
@patch("app.agents.manager.ResearchGapAgent")
@patch("app.agents.manager.HypothesisGeneratorAgent")
@patch("app.agents.manager.DebateAgent")
@patch("app.agents.manager.DatasetDiscoveryAgent")
@patch("app.agents.manager.ExperimentPlannerAgent")
@patch("app.agents.manager.CodeGenerationAgent")
@patch("app.agents.manager.ExperimentExecutionAgent")
@patch("app.agents.manager.EvaluationAgent")
@patch("app.agents.manager.ScientificWriterAgent")
@patch("app.agents.manager.PeerReviewerAgent")
@patch("app.agents.manager.MemoryAgent")
@patch("app.agents.manager.KnowledgeGraphAgent")
@patch("app.agents.manager.analyze_reach_evidence")
async def test_manager_revision_loop(
    mock_reach, mock_graph, mock_memory, mock_reviewer, mock_writer,
    mock_eval, mock_exec, mock_codegen, mock_planner, mock_dataset,
    mock_debate, mock_hypo, mock_gap, mock_lit
):
    db = TestingSessionLocal()
    try:
        # Create project and stages in DB
        project = Project(title="Revision Loop Project", description="Testing loop logic", user_id=1, status="idle")
        db.add(project)
        db.commit()
        db.refresh(project)
        
        stages = ["literature", "gap", "hypothesis", "debate", "dataset", "planning", "coding", "execution", "evaluation", "writing", "review", "memory", "graph"]
        for stage_name in stages:
            db_stage = ResearchStage(project_id=project.id, stage_name=stage_name, status="pending")
            db.add(db_stage)
        db.commit()

        # Mock agent execute returns
        mock_lit.return_value.execute = AsyncMock(return_value={})
        mock_gap.return_value.execute = AsyncMock(return_value={})
        mock_hypo.return_value.execute = AsyncMock(return_value={})
        mock_debate.return_value.execute = AsyncMock(return_value={})
        mock_dataset.return_value.execute = AsyncMock(return_value={})
        mock_planner.return_value.execute = AsyncMock(return_value={})
        
        # Mock CodeGen and Writer to trace calls
        mock_codegen.return_value.execute = AsyncMock(return_value={"files_generated": 5})
        mock_exec.return_value.execute = AsyncMock(return_value={})
        mock_eval.return_value.execute = AsyncMock(return_value={})
        mock_writer.return_value.execute = AsyncMock(return_value={"paper_id": 1})
        mock_memory.return_value.execute = AsyncMock(return_value={})
        mock_graph.return_value.execute = AsyncMock(return_value={})
        mock_reach.return_value = {"items": []}

        # Mock reviewer to fail first, then pass
        # The first call returns score = 8.0 (triggers revision loop)
        # The second call returns score = 9.0 (exits loop)
        mock_reviewer.return_value.execute = AsyncMock()
        mock_reviewer.return_value.execute.side_effect = [
            {"score": 8.0, "comments": {"Methodology": "Data leakage"}, "suggestions": ["Use patient-level split"]},
            {"score": 9.0, "comments": {}, "suggestions": []}
        ]

        # Instantiate ResearchManager
        manager = ResearchManager(db, project.id)
        
        # Bypass HITL pausing by automatically setting stages to approved if they get paused
        original_wait = manager._wait_for_approval
        async def mock_wait(stage_name):
            stage = db.query(ResearchStage).filter(
                ResearchStage.project_id == project.id,
                ResearchStage.stage_name == stage_name
            ).first()
            if stage:
                stage.is_approved = True
                db.commit()
            return await original_wait(stage_name)
        
        manager._wait_for_approval = mock_wait

        # Run pipeline
        await manager.run_pipeline("Brain Tumor Detection")

        # Verify CodeGen execution was called twice (initial + revision)
        assert mock_codegen.return_value.execute.call_count == 2
        
        # The second call should have been passed peer review comments/suggestions
        # Let's inspect the call arguments
        second_call_args = mock_codegen.return_value.execute.call_args_list[1]
        assert "review_feedback" in second_call_args[1]
        assert "Data leakage" in second_call_args[1]["review_feedback"]
        assert "Use patient-level split" in second_call_args[1]["review_feedback"]

        # Verify Writer execution was called twice
        assert mock_writer.return_value.execute.call_count == 2
        second_writer_call_args = mock_writer.return_value.execute.call_args_list[1]
        assert "review_feedback" in second_writer_call_args[1]

        # Verify Reviewer execution was called twice
        assert mock_reviewer.return_value.execute.call_count == 2
        
    finally:
        db.close()


@pytest.mark.anyio
async def test_premium_features():
    db = TestingSessionLocal()
    try:
        # Create a project
        project = Project(title="Premium Features Test Project", description="Testing explorer, terminal, CoT, and HF", user_id=1, status="idle")
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Test CoT reasoning_chain stage storage
        stage = ResearchStage(
            project_id=project.id,
            stage_name="literature",
            status="pending",
            reasoning_chain=[]
        )
        db.add(stage)
        db.commit()
        
        # Let's use the BaseAgent reason_step method
        from app.agents.base import BaseAgent
        agent = BaseAgent(db, project.id, "literature")
        agent.start_stage()
        agent.reason_step("Scanning literature for invariant parameters", "thought")
        
        # Check DB stage reasoning_chain
        db.refresh(stage)
        assert stage.reasoning_chain is not None
        assert len(stage.reasoning_chain) == 1
        assert stage.reasoning_chain[0]["message"] == "Scanning literature for invariant parameters"
        assert stage.reasoning_chain[0]["type"] == "thought"

        # Mock client to call our API endpoints
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # We need user authentication or we can mock get_current_user
        # Let's register a user and log in to get access token
        user_data = {"email": "tester@example.com", "password": "securepassword", "full_name": "Test User", "role": "researcher"}
        register_res = client.post("/api/v1/auth/register", json=user_data)
        assert register_res.status_code in [200, 400]
        
        login_res = client.post("/api/v1/auth/login", data={"username": "tester@example.com", "password": "securepassword"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test Hugging Face publisher route
        hf_res = client.post(f"/api/v1/projects/{project.id}/publish/hf", headers=headers)
        assert hf_res.status_code == 200
        assert "repository_url" in hf_res.json()
        assert "arsa-ai/premium-features-test-project" in hf_res.json()["repository_url"]
        
        # Test sandbox file explorer list API
        list_res = client.get(f"/api/v1/projects/{project.id}/sandbox/files", headers=headers)
        assert list_res.status_code == 200
        assert "files" in list_res.json()
        
        # Test sandbox terminal execution API
        term_res = client.post(
            f"/api/v1/projects/{project.id}/sandbox/terminal",
            json={"command": "echo 'hello test'"},
            headers=headers
        )
        assert term_res.status_code == 200
        assert "stdout" in term_res.json()
        
        # Test sandbox terminal block patterns
        term_block_res = client.post(
            f"/api/v1/projects/{project.id}/sandbox/terminal",
            json={"command": "rm -rf ."},
            headers=headers
        )
        assert term_block_res.status_code == 403
        
    finally:
        db.close()


@pytest.mark.anyio
async def test_agent_reach_integration():
    from app.utils.reach import analyze_reach_evidence
    res = await analyze_reach_evidence("Brain Tumor Detection")
    
    assert res is not None
    assert "evidence_score" in res
    assert "community_validation_score" in res
    assert "items" in res
    assert len(res["items"]) == 3
    
    sources = [item["source"] for item in res["items"]]
    assert "GitHub" in sources or "Agent-Reach (GitHub)" in sources
