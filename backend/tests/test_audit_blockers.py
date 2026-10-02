import pytest
import asyncio
from app.core.database import SessionLocal
from app.models.models import User, Project, ResearchStage, BillingTransaction, DocumentEmbedding
from app.services.billing_service import billing_service
from app.agents.manager import ResearchManager
from app.utils.vector_store import SimpleVectorStore, _generate_dense_fallback_embedding

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

def test_blocker_3_1_commercial_billing(db_session):
    """Verify commercial operations, quota enforcement, and atomic transactions."""
    user = User(
        email="test_commercial@example.com",
        hashed_password="secure_password_hash",
        full_name="Commercial Test User",
        subscription_tier="free",
        balance_usd=1.00,  # Below minimum run cost ($2.50)
        compute_quota_gpu_hours=10.0,
        compute_used_gpu_hours=0.0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        title="Commercial Verification Project",
        description="Testing preflight commercial checks",
        status="idle",
        user_id=user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    try:
        # 1. Verify rejection when balance is insufficient
        authorized, reason, tx = billing_service.check_and_deduct_pipeline_funds(db_session, user, project.id)
        assert authorized is False
        assert "Insufficient funds" in reason
        assert tx is None

        # 2. Deposit funds
        dep_tx = billing_service.deposit_funds(db_session, user, 10.00, "stripe_card")
        assert dep_tx.amount_usd == 10.00
        assert user.balance_usd == 11.00

        # 3. Successful deduction
        auth2, reason2, tx2 = billing_service.check_and_deduct_pipeline_funds(db_session, user, project.id)
        assert auth2 is True
        assert user.balance_usd == 8.50
        assert tx2.amount_usd == -2.50

        # 4. Pro Tier unlimited execution
        sub_tx = billing_service.upgrade_subscription(db_session, user, "pro")
        assert user.subscription_tier == "pro"
        assert user.compute_quota_gpu_hours == 500.0
        
        auth3, reason3, tx3 = billing_service.check_and_deduct_pipeline_funds(db_session, user, project.id)
        assert auth3 is True
        assert user.balance_usd == 8.50  # Unlimited under pro, no balance deducted!
        assert tx3.amount_usd == 0.0

        # 5. Billing summary
        summary = billing_service.get_summary(db_session, user)
        assert summary["subscription_tier"] == "pro"
        assert summary["balance_usd"] == 8.50
        assert len(summary["transactions"]) >= 3
    finally:
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()

def test_blocker_3_2_task_loss_recovery_and_resumption(db_session):
    """Verify zombie project recovery on restart and zero-loss stage resumption."""
    user = User(
        email="test_resumption@example.com",
        hashed_password="secure_password_hash",
        full_name="Resumption Test User",
        subscription_tier="pro"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        title="Fault-Tolerant Distributed Research Project",
        status="running",  # Simulating active pipeline when server terminates
        user_id=user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    stage_lit = ResearchStage(
        project_id=project.id,
        stage_name="literature",
        status="completed",
        output_data={"papers": [{"title": "Foundation Models for Science"}]}
    )
    stage_gap = ResearchStage(
        project_id=project.id,
        stage_name="gap",
        status="active"  # Simulating stage in progress when server died
    )
    db_session.add_all([stage_lit, stage_gap])
    db_session.commit()

    try:
        # Simulate startup lifespan recovery
        zombies = db_session.query(Project).filter(Project.status == "running").all()
        for p in zombies:
            p.status = "interrupted"
            for st in p.stages:
                if st.status in ("active", "running"):
                    st.status = "interrupted"
                    st.user_feedback = "Interrupted by system restart. Ready to resume."
        db_session.commit()

        db_session.refresh(project)
        db_session.refresh(stage_gap)
        assert project.status == "interrupted"
        assert stage_gap.status == "interrupted"

        # Test resumption awareness
        manager = ResearchManager(db=db_session, project_id=project.id)
        lit_done, lit_data = manager._is_stage_completed("literature")
        assert lit_done is True
        assert lit_data is not None

        gap_done, _ = manager._is_stage_completed("gap")
        assert gap_done is False  # Incomplete stage must execute on resume!
    finally:
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()

def test_blocker_3_3_persistent_vector_store():
    """Verify vector store persistence in SQLite and absence of global failure latch."""
    async def _async_test():
        collection = "audit_verification_docs"
        store1 = SimpleVectorStore(collection)
        store1.clear()

        docs = [
            "Contrastive self-supervised learning for medical pathology imaging.",
            "Quantum error correction codes in fault-tolerant superconducting qubits."
        ]
        metas = [{"domain": "medical"}, {"domain": "quantum"}]
        ids = ["doc_med", "doc_quant"]

        await store1.add(docs, metas, ids)
        assert len(store1.documents) == 2

        # Query
        res = await store1.query("pathology biopsy classification", n_results=1)
        assert len(res["documents"]) == 1
        assert "pathology" in res["documents"][0]

        # Verify persistent rehydration across store instances (survives restart)
        store2 = SimpleVectorStore(collection)
        assert len(store2.documents) == 2
        assert "doc_med" in store2.ids
        assert "doc_quant" in store2.ids

        # Cleanup
        store2.clear()
        store3 = SimpleVectorStore(collection)
        assert len(store3.documents) == 0

    asyncio.run(_async_test())

def test_blocker_4_1_rate_limiting():
    """Verify SlowAPI rate limiting enforces limits and returns 429 Too Many Requests."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # /auth/login is limited to 10/minute per IP
    responses = []
    for _ in range(12):
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "attacker@bruteforce.com", "password": "wrongpassword"}
        )
        responses.append(resp.status_code)

    # At least one request beyond the limit must return 429 Too Many Requests
    assert 429 in responses, f"Expected 429 Too Many Requests in responses, got {responses}"

def test_blocker_4_2_websocket_inband_auth(db_session):
    """Verify OWASP compliance: WebSocket connects without URL query token and authenticates via in-band frame."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    # Create test user & project
    user = User(
        email="ws_auth_test@example.com",
        hashed_password="pw",
        full_name="WS Test User",
        role="researcher"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        title="WS In-Band Handshake Test",
        status="idle",
        user_id=user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    try:
        valid_token = create_access_token(subject=user.email)
        client = TestClient(app)

        # 1. Connect without token in URL query parameter (clean URL)
        with client.websocket_connect(f"/ws/projects/{project.id}") as websocket:
            # Transmit in-band authentication frame
            websocket.send_json({"type": "auth", "token": valid_token})
            auth_ack = websocket.receive_json()
            assert auth_ack["type"] == "authenticated"
            assert "verified" in auth_ack["message"].lower()

        # 2. Test invalid credentials in in-band frame
        try:
            with client.websocket_connect(f"/ws/projects/{project.id}") as bad_ws:
                bad_ws.send_json({"type": "auth", "token": "invalid_forged_secret"})
                bad_ws.receive_json()
        except Exception:
            # WebSocket should be closed with policy violation
            pass
    finally:
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()

def test_security_5_1_httponly_cookie_authentication(db_session):
    """Verify Security 5.1: Session JWT is transmitted via secure HttpOnly cookie and authenticates without localStorage."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash

    # 1. Create test user
    test_email = "cookie_auth_test@arsa.org"
    user = User(
        email=test_email,
        hashed_password=get_password_hash("StrongSecret123!"),
        full_name="Cookie Test Researcher",
        role="researcher"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    client = TestClient(app)

    try:
        # 2. Login via POST /auth/login
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": "StrongSecret123!"}
        )
        assert login_resp.status_code == 200
        # Check that response set-cookie header contains access_token with HttpOnly
        set_cookie = login_resp.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "httponly" in set_cookie.lower()

        # 3. Call /auth/me with NO Authorization header (solely using HttpOnly cookie)
        # Note: TestClient automatically stores cookies from responses
        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["email"] == test_email
        assert me_data["full_name"] == "Cookie Test Researcher"

        # 4. Logout via POST /auth/logout
        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200

        # 5. Subsequent request to /auth/me must now fail with 401
        post_logout_me = client.get("/api/v1/auth/me")
        assert post_logout_me.status_code == 401
    finally:
        db_session.delete(user)
        db_session.commit()

def test_security_5_2_password_reset_and_mfa_flow(db_session):
    """Verify Security 5.2: Complete Password Reset and RFC 6238 TOTP Multi-Factor Authentication flow."""
    import pyotp
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash, create_access_token

    test_email = "mfa_reset_test@arsa.org"
    initial_pw = "InitialPass123!"
    updated_pw = "BrandNewSecurePass999!"

    user = User(
        email=test_email,
        hashed_password=get_password_hash(initial_pw),
        full_name="MFA Test Scientist",
        role="researcher"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    client = TestClient(app)

    try:
        # --- PART A: PASSWORD RESET FLOW ---
        # 1. Non-existent email returns generic success (prevents user enumeration)
        non_existent_resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@doesnotexist.com"}
        )
        assert non_existent_resp.status_code == 200
        assert "instructions have been dispatched" in non_existent_resp.json()["message"]

        # 2. Existing user requests password reset
        forgot_resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_email}
        )
        assert forgot_resp.status_code == 200
        reset_token = forgot_resp.json().get("reset_token")
        assert reset_token is not None, "Reset token should be exposed in testing environment"

        # 3. Invalid token fails
        invalid_reset = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "forged_invalid_token", "new_password": updated_pw}
        )
        assert invalid_reset.status_code == 400

        # 4. Valid token successfully updates password
        valid_reset = client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": updated_pw}
        )
        assert valid_reset.status_code == 200
        assert "successfully updated" in valid_reset.json()["message"]

        # 5. Old password no longer works
        old_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": initial_pw}
        )
        assert old_login.status_code == 400

        # 6. New password successfully logs in
        new_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": updated_pw}
        )
        assert new_login.status_code == 200
        auth_token = new_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {auth_token}"}

        # --- PART B: MULTI-FACTOR AUTHENTICATION (MFA) FLOW ---
        # 1. Setup MFA: Generate Base32 secret and otpauth URI
        setup_resp = client.post("/api/v1/auth/mfa/setup", headers=headers)
        assert setup_resp.status_code == 200
        mfa_data = setup_resp.json()
        secret = mfa_data["secret"]
        assert "otpauth://" in mfa_data["otpauth_url"]

        # 2. Enable MFA with invalid code fails
        bad_enable = client.post(
            "/api/v1/auth/mfa/enable",
            headers=headers,
            json={"code": "000000"}
        )
        assert bad_enable.status_code == 400

        # 3. Enable MFA with valid live TOTP code succeeds
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        good_enable = client.post(
            "/api/v1/auth/mfa/enable",
            headers=headers,
            json={"code": valid_code}
        )
        assert good_enable.status_code == 200
        assert "successfully enabled" in good_enable.json()["message"]

        # 4. Subsequent login without MFA challenge returns mfa_required=True
        mfa_challenge_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": updated_pw}
        )
        assert mfa_challenge_login.status_code == 200
        assert mfa_challenge_login.json().get("mfa_required") is True
        assert mfa_challenge_login.json().get("access_token") is None

        # 5. Login with invalid MFA code fails
        bad_mfa_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": updated_pw, "mfa_code": "999999"}
        )
        assert bad_mfa_login.status_code == 400

        # 6. Login with valid MFA code succeeds and issues token
        live_code = totp.now()
        good_mfa_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": updated_pw, "mfa_code": live_code}
        )
        assert good_mfa_login.status_code == 200
        assert good_mfa_login.json().get("access_token") is not None
        assert good_mfa_login.json().get("mfa_required") is False

        # 7. Disable MFA using account password and valid TOTP code
        disable_resp = client.post(
            "/api/v1/auth/mfa/disable",
            headers={"Authorization": f"Bearer {good_mfa_login.json()['access_token']}"},
            json={"password": updated_pw, "code": totp.now()}
        )
        assert disable_resp.status_code == 200

        # 8. Normal login without MFA code works again
        final_login = client.post(
            "/api/v1/auth/login",
            data={"username": test_email, "password": updated_pw}
        )
        assert final_login.status_code == 200
        assert final_login.json().get("mfa_required") is False
    finally:
        db_session.delete(user)
        db_session.commit()


def test_data_integrity_6_1_saga_cleanup_and_idempotency(db_session):
    """
    Test [HIGH] 6.1: Idempotent Stage Saga Execution & Compensating Cleanup.
    Verifies that:
    1. Re-running a stage or recovering after failure purges previous intermediate artifacts;
    2. Zero duplicate records are generated on retries;
    3. Stage failures cleanly record error status without corrupting previous stages.
    """
    from app.models.models import (
        User, Project, ResearchStage, LiteraturePaper, ResearchGap,
        Hypothesis, DebateLog, DatasetRecommendation, ExperimentPlan,
        GeneratedFile, ExperimentRun, ScientificPaper, PeerReview,
        KnowledgeNode, KnowledgeEdge
    )
    from app.agents.manager import ResearchManager
    from app.core.security import get_password_hash

    # Create test user and project
    user = User(
        email="saga_test_user@arsa.org",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Saga Integrity Scientist",
        role="researcher"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        title="Robust Latent Disentanglement",
        description="Testing saga transactions and stage idempotency",
        user_id=user.id,
        status="idle"
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    try:
        manager = ResearchManager(db=db_session, project_id=project.id)

        # 1. Populate dummy artifacts for literature, gap, and coding stages
        paper1 = LiteraturePaper(project_id=project.id, title="Paper A", relevance_score=9.0)
        paper2 = LiteraturePaper(project_id=project.id, title="Paper B", relevance_score=8.5)
        node_p1 = KnowledgeNode(id="paper-100", project_id=project.id, type="paper", label="Paper A")
        edge_p1 = KnowledgeEdge(project_id=project.id, source="paper-100", target="gap-100", type="arises_from")
        db_session.add_all([paper1, paper2, node_p1, edge_p1])

        gap1 = ResearchGap(project_id=project.id, description="### Gap 1", novelty_score=90.0, opportunity_score=92.0)
        node_g1 = KnowledgeNode(id="gap-100", project_id=project.id, type="gap", label="Gap 1")
        db_session.add_all([gap1, node_g1])

        file1 = GeneratedFile(project_id=project.id, filepath="model.py", content="# initial code", explanation="Initial")
        file2 = GeneratedFile(project_id=project.id, filepath="train.py", content="# initial train", explanation="Initial")
        db_session.add_all([file1, file2])

        db_session.commit()

        # Verify artifacts exist
        assert db_session.query(LiteraturePaper).filter(LiteraturePaper.project_id == project.id).count() == 2
        assert db_session.query(ResearchGap).filter(ResearchGap.project_id == project.id).count() == 1
        assert db_session.query(GeneratedFile).filter(GeneratedFile.project_id == project.id).count() == 2

        # 2. Trigger saga cleanup on literature stage
        manager._clean_stage_artifacts("literature")
        assert db_session.query(LiteraturePaper).filter(LiteraturePaper.project_id == project.id).count() == 0
        assert db_session.query(KnowledgeNode).filter(KnowledgeNode.project_id == project.id, KnowledgeNode.type == "paper").count() == 0
        # Gap and coding artifacts remain intact
        assert db_session.query(ResearchGap).filter(ResearchGap.project_id == project.id).count() == 1
        assert db_session.query(GeneratedFile).filter(GeneratedFile.project_id == project.id).count() == 2

        # 3. Test failed stage handling and rollback inside _execute_stage
        # Create stage record
        stage_rec = ResearchStage(
            project_id=project.id,
            stage_name="execution",
            status="pending"
        )
        db_session.add(stage_rec)
        db_session.commit()

        async def _async_test_flow():
            class FaultyAgent:
                def __init__(self, db, pid):
                    self.db = db
                    self.project_id = pid
                async def execute(self):
                    # Write an uncommitted partial record, then raise an error
                    bad_run = ExperimentRun(project_id=self.project_id, status="broken")
                    self.db.add(bad_run)
                    raise RuntimeError("Simulated GPU Hardware Timeout during training loop")
                def fail_stage(self, err):
                    pass

            with pytest.raises(RuntimeError) as exc_info:
                await manager._execute_stage(
                    "execution",
                    lambda: FaultyAgent(db_session, project.id),
                    resume=False
                )
            assert "Simulated GPU Hardware Timeout" in str(exc_info.value)

            # Confirm uncommitted partial runs were rolled back and stage marked failed
            db_session.expire_all()
            stage_check = db_session.query(ResearchStage).filter(
                ResearchStage.project_id == project.id,
                ResearchStage.stage_name == "execution"
            ).first()
            assert stage_check.status == "failed"
            assert "Simulated GPU Hardware Timeout" in stage_check.user_feedback
            assert db_session.query(ExperimentRun).filter(ExperimentRun.project_id == project.id).count() == 0

            # 4. Re-running the stage after failure cleanly succeeds and is idempotent
            class SuccessfulAgent:
                def __init__(self, db, pid):
                    self.db = db
                    self.project_id = pid
                async def execute(self):
                    run = ExperimentRun(project_id=self.project_id, status="completed", logs="Success")
                    self.db.add(run)
                    self.db.commit()
                    stage = self.db.query(ResearchStage).filter(
                        ResearchStage.project_id == self.project_id,
                        ResearchStage.stage_name == "execution"
                    ).first()
                    if stage:
                        stage.status = "completed"
                        stage.output_data = {"run_id": run.id, "accuracy": 96.5}
                        self.db.commit()
                    return {"status": "completed"}

            res1 = await manager._execute_stage(
                "execution",
                lambda: SuccessfulAgent(db_session, project.id),
                resume=False
            )
            assert res1["status"] == "completed"
            assert db_session.query(ExperimentRun).filter(ExperimentRun.project_id == project.id).count() == 1

            # Re-running again with resume=False cleans previous run and avoids duplicate records
            res2 = await manager._execute_stage(
                "execution",
                lambda: SuccessfulAgent(db_session, project.id),
                resume=False
            )
            assert res2["status"] == "completed"
            assert db_session.query(ExperimentRun).filter(ExperimentRun.project_id == project.id).count() == 1

        asyncio.run(_async_test_flow())

    finally:
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()


def test_data_integrity_6_2_immutable_audit_logging(db_session):
    """
    Test [MEDIUM] 6.2: Immutable Audit Logging across Critical Operations.
    Verifies that:
    1. Terminal commands, sandbox writes, code edits, and stage approvals produce immutable audit logs;
    2. Audit logs record actor user ID, client IP, action, and structured details;
    3. GET /projects/{id}/audit-logs delivers complete audit trail for compliance;
    4. GET /admin/audit-logs allows administrators to inspect system-wide events.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.models import User, Project, GeneratedFile, ResearchStage, AuditLog
    from app.core.security import get_password_hash, create_access_token

    admin_email = "audit_admin@arsa.org"
    user_email = "audit_user@arsa.org"

    admin_user = User(
        email=admin_email,
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Compliance Officer",
        role="administrator"
    )
    norm_user = User(
        email=user_email,
        hashed_password=get_password_hash("UserPass123!"),
        full_name="Lead Researcher",
        role="researcher"
    )
    db_session.add_all([admin_user, norm_user])
    db_session.commit()
    db_session.refresh(admin_user)
    db_session.refresh(norm_user)

    project = Project(
        title="Cancer Detection Benchmark",
        description="Clinical Trial Audit Test",
        user_id=norm_user.id,
        status="idle"
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    stage = ResearchStage(
        project_id=project.id,
        stage_name="literature",
        status="active"
    )
    code_file = GeneratedFile(
        project_id=project.id,
        filepath="pipeline.py",
        content="print('v1.0')",
        explanation="Version 1"
    )
    db_session.add_all([stage, code_file])
    db_session.commit()
    db_session.refresh(code_file)

    user_token = create_access_token(subject=user_email)
    admin_token = create_access_token(subject=admin_email)
    user_headers = {"Authorization": f"Bearer {user_token}", "X-Forwarded-For": "198.51.100.42"}
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Forwarded-For": "198.51.100.99"}

    client = TestClient(app)

    try:
        # 1. Action: Sandbox Terminal Execution
        term_resp = client.post(
            f"/api/v1/projects/{project.id}/sandbox/terminal",
            headers=user_headers,
            json={"command": "python -c \"print('Hello Compliance')\""}
        )
        assert term_resp.status_code == 200

        # 2. Action: Sandbox File Write
        write_resp = client.put(
            f"/api/v1/projects/{project.id}/sandbox/files/write",
            headers=user_headers,
            json={"path": "audit_evidence.txt", "content": "Evidence of reproducibility."}
        )
        assert write_resp.status_code == 200

        # 3. Action: Source Code Modification
        code_resp = client.put(
            f"/api/v1/projects/{project.id}/code/{code_file.id}",
            headers=user_headers,
            json={"content": "print('v2.0 - Verified')"}
        )
        assert code_resp.status_code == 200

        # 4. Action: Stage Approval with Feedback
        approve_resp = client.post(
            f"/api/v1/projects/{project.id}/stages/literature/approve",
            headers=user_headers,
            json={"is_approved": True, "feedback": "Methodology conforms to FDA 21 CFR Part 11 guidelines."}
        )
        assert approve_resp.status_code == 200

        # 5. Retrieve project audit logs via GET /api/v1/projects/{id}/audit-logs
        audit_resp = client.get(
            f"/api/v1/projects/{project.id}/audit-logs",
            headers=user_headers
        )
        assert audit_resp.status_code == 200
        logs = audit_resp.json()
        assert len(logs) >= 4, f"Expected at least 4 audit log entries, found {len(logs)}"

        actions = [l["action"] for l in logs]
        assert "sandbox_command" in actions
        assert "file_write" in actions
        assert "code_update" in actions
        assert "stage_approved" in actions

        # Check provenance details
        for entry in logs:
            assert entry["project_id"] == project.id
            assert entry["user_id"] == norm_user.id
            assert entry["ip_address"] == "198.51.100.42"
            assert "created_at" in entry
            assert entry["details"] is not None

        # 6. Verify Admin-only system-wide audit access
        # Researcher cannot access admin audit logs
        forbidden_audit = client.get("/api/v1/admin/audit-logs", headers=user_headers)
        assert forbidden_audit.status_code == 403

        # Administrator can access admin audit logs
        admin_audit = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert admin_audit.status_code == 200
        admin_logs = admin_audit.json()
        assert len(admin_logs) >= 4

    finally:
        db_session.delete(project)
        db_session.delete(norm_user)
        db_session.delete(admin_user)
        db_session.commit()

def test_precision_7_1_numeric_scoring(db_session):
    """Verify Category 7.1: Fixed-point Numeric scoring prevents floating-point rounding errors and erratic threshold checks."""
    from decimal import Decimal
    from app.models.models import LiteraturePaper, ResearchGap, Hypothesis, ScientificPaper, PeerReview

    test_user = User(
        email="precision_tester@example.com",
        hashed_password="pw",
        full_name="Precision Tester",
        role="researcher"
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    project = Project(
        title="Precision Scoring Test",
        status="idle",
        user_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    try:
        # 1. Test LiteraturePaper relevance_score precision
        paper = LiteraturePaper(
            project_id=project.id,
            title="Deep Residual Learning",
            relevance_score=Decimal("8.50")
        )
        db_session.add(paper)

        # 2. Test ResearchGap novelty and opportunity score precision
        gap = ResearchGap(
            project_id=project.id,
            description="### Latent Domain Adaptation\nTesting precision",
            novelty_score=Decimal("94.75"),
            opportunity_score=Decimal("89.20")
        )
        db_session.add(gap)

        # 3. Test Hypothesis confidence_level precision (Numeric(5, 4))
        hyp = Hypothesis(
            project_id=project.id,
            statement="Self-supervised pretraining minimizes cross-scanner variance.",
            confidence_level=Decimal("0.8925")
        )
        db_session.add(hyp)

        # 4. Test ScientificPaper and PeerReview threshold boundary
        sc_paper = ScientificPaper(
            project_id=project.id,
            title="Scientific Manuscript on Generalization",
            publication_readiness_score=Decimal("8.50")
        )
        db_session.add(sc_paper)
        db_session.commit()
        db_session.refresh(sc_paper)

        # Peer review score: simulate borderline 8.499999999999999
        borderline_score = round(float(8.499999999999999), 2)  # evaluates to 8.50
        review = PeerReview(
            paper_id=sc_paper.id,
            score=borderline_score,
            comments={"overall": "Solid contribution"}
        )
        db_session.add(review)
        db_session.commit()

        # Query back and verify Decimal/fixed-point preservation
        db_session.refresh(paper)
        db_session.refresh(gap)
        db_session.refresh(hyp)
        db_session.refresh(review)

        assert round(float(paper.relevance_score), 2) == 8.50
        assert round(float(gap.novelty_score), 2) == 94.75
        assert round(float(gap.opportunity_score), 2) == 89.20
        assert round(float(hyp.confidence_level), 4) == 0.8925
        assert round(float(review.score), 2) == 8.50

        # Verify automated revision loop threshold: score 8.50 must NOT trigger revision (< 8.5)
        should_revise = round(float(review.score), 2) < 8.5
        assert should_revise is False

        # But a true 8.49 score MUST trigger revision
        sub_threshold_score = round(float(8.49), 2)
        assert (sub_threshold_score < 8.5) is True

    finally:
        db_session.delete(project)
        db_session.delete(test_user)
        db_session.commit()

def test_validation_7_2_payload_boundaries(db_session):
    """Verify Category 7.2: Unbounded text payloads are rejected with HTTP 422 Unprocessable Entity."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.models.models import GeneratedFile, ResearchStage

    user_email = "boundary_tester@example.com"
    user = User(
        email=user_email,
        hashed_password="pw",
        full_name="Boundary Tester",
        role="researcher"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(subject=user_email)
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    # 1. Project creation with empty title -> 422
    resp_empty = client.post("/api/v1/projects", headers=headers, json={"title": ""})
    assert resp_empty.status_code == 422

    # 2. Project creation with whitespace-only title -> 422
    resp_ws = client.post("/api/v1/projects", headers=headers, json={"title": "     "})
    assert resp_ws.status_code == 422

    # 3. Project creation with title > 255 chars -> 422
    long_title = "A" * 256
    resp_long_title = client.post("/api/v1/projects", headers=headers, json={"title": long_title})
    assert resp_long_title.status_code == 422

    # 4. Project creation with description > 5000 chars -> 422
    long_desc = "B" * 5001
    resp_long_desc = client.post("/api/v1/projects", headers=headers, json={"title": "Valid Title", "description": long_desc})
    assert resp_long_desc.status_code == 422

    # 5. Valid project creation -> 200
    resp_valid = client.post("/api/v1/projects", headers=headers, json={"title": "Valid Title", "description": "Valid brief description."})
    assert resp_valid.status_code == 200
    created_proj = resp_valid.json()
    proj_id = created_proj["id"]

    try:
        # 6. Stage approval with feedback > 5000 chars -> 422
        resp_feedback_overflow = client.post(
            f"/api/v1/projects/{proj_id}/stages/literature/approve",
            headers=headers,
            json={"is_approved": True, "feedback": "X" * 5001}
        )
        assert resp_feedback_overflow.status_code == 422

        # 7. Code update with empty content -> 422
        code_file = GeneratedFile(
            project_id=proj_id,
            filepath="model.py",
            content="print(1)"
        )
        db_session.add(code_file)
        db_session.commit()
        db_session.refresh(code_file)

        resp_empty_code = client.put(
            f"/api/v1/projects/{proj_id}/code/{code_file.id}",
            headers=headers,
            json={"content": ""}
        )
        assert resp_empty_code.status_code == 422

        # 8. Valid code update within limits -> 200
        resp_valid_code = client.put(
            f"/api/v1/projects/{proj_id}/code/{code_file.id}",
            headers=headers,
            json={"content": "def train(): pass"}
        )
        assert resp_valid_code.status_code == 200

    finally:
        client.delete(f"/api/v1/projects/{proj_id}", headers=headers)
        db_session.delete(user)
        db_session.commit()

def test_deployment_8_1_alembic_migrations():
    """Verify Category 8.1: Alembic migration system is configured and current revision is stamped."""
    import os
    from alembic.config import Config
    from alembic import command

    alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    assert os.path.exists(alembic_ini_path), "alembic.ini must exist in backend root"

    alembic_cfg = Config(alembic_ini_path)

    # Check that versions directory contains migration scripts
    versions_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    version_files = [f for f in os.listdir(versions_dir) if f.endswith(".py")]
    assert len(version_files) >= 1, "At least one Alembic migration script must be present in alembic/versions"

    # Verify programmatic upgrade head works cleanly
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        pytest.fail(f"Alembic upgrade head failed: {e}")

def test_deployment_8_2_database_backup_and_recovery(db_session):
    """Verify Category 8.2: Automated online SQLite backups, checksumming, retention, and disaster recovery."""
    import os
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.services.backup_service import backup_service

    # Create admin and researcher users
    admin_user = User(
        email="backup_admin@example.com",
        hashed_password="pw",
        full_name="Backup Admin",
        role="administrator"
    )
    norm_user = User(
        email="backup_norm@example.com",
        hashed_password="pw",
        full_name="Norm User",
        role="researcher"
    )
    db_session.add_all([admin_user, norm_user])
    db_session.commit()
    db_session.refresh(admin_user)
    db_session.refresh(norm_user)

    admin_token = create_access_token(subject=admin_user.email)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    norm_token = create_access_token(subject=norm_user.email)
    norm_headers = {"Authorization": f"Bearer {norm_token}"}

    client = TestClient(app)

    try:
        # 1. Non-admin cannot create or list backups (RBAC enforcement)
        forbidden_list = client.get("/api/v1/admin/backups", headers=norm_headers)
        assert forbidden_list.status_code == 403

        forbidden_create = client.post("/api/v1/admin/backups/create", headers=norm_headers, json={"label": "test"})
        assert forbidden_create.status_code == 403

        # 2. Admin creates immediate atomic database backup via REST API
        create_resp = client.post(
            "/api/v1/admin/backups/create",
            headers=admin_headers,
            json={"label": "audit_snapshot"}
        )
        assert create_resp.status_code == 200
        backup_data = create_resp.json()
        assert backup_data["filename"].endswith(".db.gz")
        assert backup_data["size_bytes"] > 0
        assert os.path.exists(os.path.join(backup_service.backup_dir, backup_data["filename"]))

        # 3. Admin lists backups
        list_resp = client.get("/api/v1/admin/backups", headers=admin_headers)
        assert list_resp.status_code == 200
        backups = list_resp.json()
        assert len(backups) >= 1
        filenames = [b["filename"] for b in backups]
        assert backup_data["filename"] in filenames

        # 4. Admin downloads backup archive
        dl_resp = client.get(f"/api/v1/admin/backups/download/{backup_data['filename']}", headers=admin_headers)
        assert dl_resp.status_code == 200
        assert len(dl_resp.content) == backup_data["size_bytes"]

        # 5. Admin restores database from snapshot
        restore_resp = client.post(
            "/api/v1/admin/backups/restore",
            headers=admin_headers,
            json={"filename": backup_data["filename"]}
        )
        assert restore_resp.status_code == 200
        restore_result = restore_resp.json()
        assert restore_result["status"] == "success"
        assert restore_result["restored_from"] == backup_data["filename"]
        assert restore_result["safety_backup"] is not None

    finally:
        db_session.delete(admin_user)
        db_session.delete(norm_user)
        db_session.commit()

def test_deployment_8_3_structured_logging_and_apm(db_session):
    """Verify Category 8.3: Structured JSON logging, trace context propagation, and APM telemetry."""
    import json
    import logging
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.core.logging import JSONFormatter, set_trace_context, apm_tracker

    # 1. Test JSONFormatter serializes record into structured JSON with trace correlation
    set_trace_context(trace_id="test-trace-12345", request_id="test-req-67890", user_id=42)
    record = logging.LogRecord(
        name="arsa.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Scientific pipeline experiment step completed",
        args=(),
        exc_info=None
    )
    record.project_id = 99
    record.stage = "coding"

    formatter = JSONFormatter()
    formatted_json_str = formatter.format(record)
    parsed = json.loads(formatted_json_str)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "arsa.test"
    assert parsed["message"] == "Scientific pipeline experiment step completed"
    assert parsed["trace_id"] == "test-trace-12345"
    assert parsed["request_id"] == "test-req-67890"
    assert parsed["user_id"] == 42
    assert parsed["project_id"] == 99
    assert parsed["stage"] == "coding"
    assert "timestamp" in parsed

    # 2. Test Request Tracing Middleware & APM metrics
    admin_user = User(
        email="apm_admin@example.com",
        hashed_password="pw",
        full_name="APM Admin",
        role="administrator"
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    admin_token = create_access_token(subject=admin_user.email)
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Request-ID": "custom-uuid-test-999"
    }

    client = TestClient(app)
    try:
        # Issue request with custom trace headers
        resp = client.get("/api/v1/projects", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == "custom-uuid-test-999"
        assert "X-Trace-ID" in resp.headers
        assert "X-Response-Time" in resp.headers

        # Verify APM metrics endpoint returns aggregated metrics
        metrics_resp = client.get("/api/v1/admin/metrics", headers=admin_headers)
        assert metrics_resp.status_code == 200
        apm_data = metrics_resp.json()
        assert apm_data["total_requests"] > 0
        assert "2xx" in apm_data["status_distribution"]
        assert "latency_ms" in apm_data
        assert "p50" in apm_data["latency_ms"]
        assert "p95" in apm_data["latency_ms"]
        assert "error_rate_pct" in apm_data

    finally:
        db_session.delete(admin_user)
        db_session.commit()



