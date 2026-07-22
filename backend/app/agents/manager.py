import asyncio
import logging
from sqlalchemy.orm import Session
from app.models.models import Project, ResearchStage
from app.agents.literature import LiteratureReviewAgent
from app.agents.gap import ResearchGapAgent
from app.agents.hypothesis import HypothesisGeneratorAgent
from app.agents.debate import DebateAgent
from app.agents.dataset import DatasetDiscoveryAgent
from app.agents.planner import ExperimentPlannerAgent
from app.agents.codegen import CodeGenerationAgent
from app.agents.execution import ExperimentExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.agents.writer import ScientificWriterAgent
from app.agents.reviewer import PeerReviewerAgent
from app.agents.memory import MemoryAgent
from app.agents.graph import KnowledgeGraphAgent
from app.utils.reach import analyze_reach_evidence
from app.models.models import AgentReachEvidence

logger = logging.getLogger("arsa.manager")

class ResearchManager:
    def __init__(self, db: Session, project_id: int):
        self.db = db
        self.project_id = project_id
        self.log_callback = None
        self.status_callback = None
        self.reasoning_callback = None

    def _on_agent_reasoning(self, step_entry: dict):
        if self.reasoning_callback:
            self.reasoning_callback(step_entry)

    def _set_project_status(self, status: str):
        project = self.db.query(Project).get(self.project_id)
        if project:
            project.status = status
            self.db.commit()
            if self.status_callback:
                self.status_callback(status)

    async def run_pipeline(self, topic: str):
        """
        Execute the full 13-stage AI Scientist research pipeline.
        """
        self._set_project_status("running")
        self.log(f"=== INITIALIZING RESEARCH PIPELINE FOR TOPIC: '{topic}' ===")
        
        try:
            # 1. Literature Review
            lit_agent = LiteratureReviewAgent(self.db, self.project_id)
            lit_agent.on_log_callback = self._on_agent_log
            lit_agent.on_reasoning_callback = self._on_agent_reasoning
            lit_results = await lit_agent.execute(topic)
            
            # 2. Research Gap
            gap_agent = ResearchGapAgent(self.db, self.project_id)
            gap_agent.on_log_callback = self._on_agent_log
            gap_agent.on_reasoning_callback = self._on_agent_reasoning
            gap_results = await gap_agent.execute()
            
            # 3. Hypothesis Generation
            hypo_agent = HypothesisGeneratorAgent(self.db, self.project_id)
            hypo_agent.on_log_callback = self._on_agent_log
            hypo_agent.on_reasoning_callback = self._on_agent_reasoning
            hypo_results = await hypo_agent.execute()
            
            # 4. Agent Debate
            debate_agent = DebateAgent(self.db, self.project_id)
            debate_agent.on_log_callback = self._on_agent_log
            debate_agent.on_reasoning_callback = self._on_agent_reasoning
            debate_results = await debate_agent.execute()
            
            # Wait for Hypothesis Approval
            await self._wait_for_approval("debate")
            
            # 5. Dataset Discovery
            dataset_agent = DatasetDiscoveryAgent(self.db, self.project_id)
            dataset_agent.on_log_callback = self._on_agent_log
            dataset_agent.on_reasoning_callback = self._on_agent_reasoning
            dataset_results = await dataset_agent.execute()
            
            # 6. Experiment Planner
            planner_agent = ExperimentPlannerAgent(self.db, self.project_id)
            planner_agent.on_log_callback = self._on_agent_log
            planner_agent.on_reasoning_callback = self._on_agent_reasoning
            planner_results = await planner_agent.execute()
            
            # 7. Code Generation
            codegen_agent = CodeGenerationAgent(self.db, self.project_id)
            codegen_agent.on_log_callback = self._on_agent_log
            codegen_agent.on_reasoning_callback = self._on_agent_reasoning
            codegen_results = await codegen_agent.execute()
            
            # Wait for Code Verification
            await self._wait_for_approval("coding")
            
            # 8. Experiment Execution
            execution_agent = ExperimentExecutionAgent(self.db, self.project_id)
            execution_agent.on_log_callback = self._on_agent_log
            execution_agent.on_reasoning_callback = self._on_agent_reasoning
            execution_results = await execution_agent.execute()
            
            # 9. Evaluation
            evaluation_agent = EvaluationAgent(self.db, self.project_id)
            evaluation_agent.on_log_callback = self._on_agent_log
            evaluation_agent.on_reasoning_callback = self._on_agent_reasoning
            evaluation_results = await evaluation_agent.execute()
            
            # 10. Scientific Writer
            writer_agent = ScientificWriterAgent(self.db, self.project_id)
            writer_agent.on_log_callback = self._on_agent_log
            writer_agent.on_reasoning_callback = self._on_agent_reasoning
            writer_results = await writer_agent.execute()
            
            # 11. Peer Reviewer
            reviewer_agent = PeerReviewerAgent(self.db, self.project_id)
            reviewer_agent.on_log_callback = self._on_agent_log
            reviewer_agent.on_reasoning_callback = self._on_agent_reasoning
            reviewer_results = await reviewer_agent.execute()
            
            # Phase 14: Automated Manuscript Revision Loop (Max 1 cycle)
            if reviewer_results.get("score", 0) < 8.5:
                self.log(f"Manuscript score is {reviewer_results.get('score')}/10.0. Revision requested. Initiating automated correction cycle...")
                
                # Format the peer review comments and suggestions
                review_feedback = ""
                if "comments" in reviewer_results:
                    review_feedback += "Critique Comments:\n"
                    comments_data = reviewer_results["comments"]
                    if isinstance(comments_data, dict):
                        for key, val in comments_data.items():
                            if isinstance(val, dict) and "critique" in val:
                                review_feedback += f"- {key.replace('_', ' ').title()} (Score: {val.get('score')}): {val.get('critique')}\n"
                            else:
                                review_feedback += f"- {key}: {val}\n"
                if "suggestions" in reviewer_results:
                    review_feedback += "\nSuggestions:\n"
                    for sug in reviewer_results["suggestions"]:
                        review_feedback += f"- {sug}\n"
                
                # Re-invoke 7. Code Generation (with feedback)
                self.log("Re-invoking CodeGen Agent with reviewer feedback...")
                codegen_agent = CodeGenerationAgent(self.db, self.project_id)
                codegen_agent.on_log_callback = self._on_agent_log
                codegen_agent.on_reasoning_callback = self._on_agent_reasoning
                codegen_results = await codegen_agent.execute(review_feedback=review_feedback)
                
                # Re-invoke 8. Experiment Execution
                self.log("Re-invoking Experiment Execution Agent...")
                execution_agent = ExperimentExecutionAgent(self.db, self.project_id)
                execution_agent.on_log_callback = self._on_agent_log
                execution_agent.on_reasoning_callback = self._on_agent_reasoning
                execution_results = await execution_agent.execute()
                
                # Re-invoke 9. Evaluation
                self.log("Re-invoking Evaluation Agent...")
                evaluation_agent = EvaluationAgent(self.db, self.project_id)
                evaluation_agent.on_log_callback = self._on_agent_log
                evaluation_agent.on_reasoning_callback = self._on_agent_reasoning
                evaluation_results = await evaluation_agent.execute()
                
                # Re-invoke 10. Scientific Writer (incorporating corrections)
                self.log("Re-invoking Scientific Writer Agent with reviewer feedback...")
                writer_agent = ScientificWriterAgent(self.db, self.project_id)
                writer_agent.on_log_callback = self._on_agent_log
                writer_agent.on_reasoning_callback = self._on_agent_reasoning
                writer_results = await writer_agent.execute(review_feedback=review_feedback)
                
                # Re-invoke 11. Peer Reviewer (re-scoring the manuscript)
                self.log("Re-invoking Peer Reviewer Agent for final scoring...")
                reviewer_agent = PeerReviewerAgent(self.db, self.project_id)
                reviewer_agent.on_log_callback = self._on_agent_log
                reviewer_agent.on_reasoning_callback = self._on_agent_reasoning
                reviewer_results = await reviewer_agent.execute()
                
                self.log(f"Automated revision loop completed. New score: {reviewer_results.get('score')}/10.0")
            
            # 12. Reach Layer & Memory Consolidation
            self.log("Activating Agent Reach Evidence integration layer...")
            reach_data = await analyze_reach_evidence(topic)
            for item in reach_data.get("items", []):
                evidence = AgentReachEvidence(
                    project_id=self.project_id,
                    source=item["source"],
                    title=item["title"],
                    url=item["url"],
                    evidence_score=item["evidence_score"],
                    community_sentiment=item["community_sentiment"],
                    summary=item["summary"]
                )
                self.db.add(evidence)
            self.db.commit()
            
            memory_agent = MemoryAgent(self.db, self.project_id)
            memory_agent.on_log_callback = self._on_agent_log
            memory_results = await memory_agent.execute(evaluation_results)
            
            # 13. Knowledge Graph Compile
            graph_agent = KnowledgeGraphAgent(self.db, self.project_id)
            graph_agent.on_log_callback = self._on_agent_log
            graph_results = await graph_agent.execute()
            
            self.log("=== FULL PIPELINE COMPLETED SUCCESSFULLY ===")
            self._set_project_status("completed")
            
        except Exception as e:
            logger.error(f"Pipeline error on project {self.project_id}: {e}", exc_info=True)
            self.log(f"=== PIPELINE TERMINATED WITH ERROR: {e} ===", "ERROR")
            self._set_project_status("failed")
            
    async def _wait_for_approval(self, stage_name: str):
        self.log(f"Pipeline paused. Waiting for supervisor approval on stage: '{stage_name}'...")
        
        # Set stage status to "paused"
        stage = self.db.query(ResearchStage).filter(
            ResearchStage.project_id == self.project_id,
            ResearchStage.stage_name == stage_name
        ).first()
        if stage:
            stage.status = "paused"
            self.db.commit()
            
            # Broadcast the paused status over WebSocket
            if self.status_callback:
                self.status_callback("paused")
                
        while True:
            # Refresh DB session
            self.db.expire_all()
            stage = self.db.query(ResearchStage).filter(
                ResearchStage.project_id == self.project_id,
                ResearchStage.stage_name == stage_name
            ).first()
            
            if stage and stage.is_approved:
                feedback_str = f"Feedback: '{stage.user_feedback}'" if stage.user_feedback else "No feedback"
                self.log(f"Stage '{stage_name}' approved. {feedback_str}. Resuming pipeline...")
                stage.status = "completed"
                self.db.commit()
                if self.status_callback:
                    self.status_callback("running")
                break
                
            await asyncio.sleep(1.0)

    def _on_agent_log(self, log_entry: dict):
        if self.log_callback:
            # Propagate up to websocket manager
            self.log_callback(log_entry)

    def log(self, message: str, level: str = "INFO"):
        # Helper to log manager level statements
        import datetime
        timestamp = datetime.datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "stage": "manager"
        }
        print(f"[MANAGER - {level}] {message}")
        if self.log_callback:
            self.log_callback(log_entry)
