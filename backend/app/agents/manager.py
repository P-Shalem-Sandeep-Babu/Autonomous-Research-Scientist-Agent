import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, Any
from sqlalchemy.orm import Session
from app.models.models import (
    Project, ResearchStage, LiteraturePaper, ResearchGap, Hypothesis, DebateLog,
    DatasetRecommendation, ExperimentPlan, GeneratedFile, ExperimentRun,
    ScientificPaper, PeerReview, KnowledgeNode, KnowledgeEdge, ResearchMemory,
    AgentReachEvidence
)
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

logger = logging.getLogger("arsa.pipeline")

# Global event registry for stage approval signals (project_id, stage_name) -> asyncio.Event
STAGE_APPROVAL_EVENTS: Dict[Tuple[int, str], asyncio.Event] = {}

def notify_stage_approved(project_id: int, stage_name: str):
    """Signals an in-flight research manager waiting for stage approval."""
    key = (project_id, stage_name)
    event = STAGE_APPROVAL_EVENTS.get(key)
    if event:
        event.set()

class ResearchManager:
    def __init__(self, db: Optional[Session] = None, project_id: int = 0):
        self.db = db
        self.project_id = project_id
        self._owns_session = False
        self.log_callback = None
        self.status_callback = None
        self.reasoning_callback = None

    def _on_agent_reasoning(self, step_entry: dict):
        if self.reasoning_callback:
            self.reasoning_callback(step_entry)

    def _set_project_status(self, status: str):
        project = self.db.get(Project, self.project_id)
        if project:
            project.status = status
            project.last_heartbeat = datetime.now(timezone.utc)
            self.db.commit()
            if self.status_callback:
                self.status_callback(status)

    def _update_checkpoint(self, stage_name: str, checkpoint_info: Optional[Dict[str, Any]] = None):
        """Updates project current stage, heartbeat timestamp, and persistent checkpoint."""
        try:
            project = self.db.get(Project, self.project_id)
            if project:
                project.current_stage = stage_name
                project.last_heartbeat = datetime.now(timezone.utc)
                if checkpoint_info:
                    existing = project.checkpoint_data or {}
                    existing.update(checkpoint_info)
                    project.checkpoint_data = existing
                self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to update checkpoint for project {self.project_id}: {e}")

    def _clean_stage_artifacts(self, stage_name: str):
        """
        Saga compensating transaction / Idempotent stage cleanup.
        Purges any intermediate or previously committed artifacts for this stage
        to ensure that re-running or retrying after a failure never produces duplicate
        records, orphaned knowledge graph nodes, or corrupt project states.
        """
        try:
            if stage_name == "literature":
                self.db.query(LiteraturePaper).filter(LiteraturePaper.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "paper").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("paper-%")) | (KnowledgeEdge.target.like("paper-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "gap":
                self.db.query(ResearchGap).filter(ResearchGap.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "gap").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("gap-%")) | (KnowledgeEdge.target.like("gap-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "hypothesis":
                self.db.query(DebateLog).filter(DebateLog.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(Hypothesis).filter(Hypothesis.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "hypothesis").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("hypothesis-%")) | (KnowledgeEdge.target.like("hypothesis-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "debate":
                self.db.query(DebateLog).filter(DebateLog.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "debate").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("debate-%")) | (KnowledgeEdge.target.like("debate-%"))
                ).delete(synchronize_session=False)
                # Reset selected flag on hypotheses
                for h in self.db.query(Hypothesis).filter(Hypothesis.project_id == self.project_id).all():
                    h.selected = False
            elif stage_name == "dataset":
                self.db.query(DatasetRecommendation).filter(DatasetRecommendation.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "dataset").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("dataset-%")) | (KnowledgeEdge.target.like("dataset-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "planning":
                self.db.query(ExperimentPlan).filter(ExperimentPlan.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "experiment").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("plan-%")) | (KnowledgeEdge.target.like("plan-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "coding":
                self.db.query(GeneratedFile).filter(GeneratedFile.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "code").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("code-%")) | (KnowledgeEdge.target.like("code-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "execution":
                self.db.query(ExperimentRun).filter(ExperimentRun.project_id == self.project_id).delete(synchronize_session=False)
            elif stage_name == "writing":
                paper_ids = [p.id for p in self.db.query(ScientificPaper.id).filter(ScientificPaper.project_id == self.project_id).all()]
                if paper_ids:
                    self.db.query(PeerReview).filter(PeerReview.paper_id.in_(paper_ids)).delete(synchronize_session=False)
                self.db.query(ScientificPaper).filter(ScientificPaper.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id, KnowledgeNode.type == "paper_writing").delete(synchronize_session=False)
                self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.project_id == self.project_id,
                    (KnowledgeEdge.source.like("paper-draft-%")) | (KnowledgeEdge.target.like("paper-draft-%"))
                ).delete(synchronize_session=False)
            elif stage_name == "review":
                paper_ids = [p.id for p in self.db.query(ScientificPaper.id).filter(ScientificPaper.project_id == self.project_id).all()]
                if paper_ids:
                    self.db.query(PeerReview).filter(PeerReview.paper_id.in_(paper_ids)).delete(synchronize_session=False)
            elif stage_name == "memory":
                self.db.query(AgentReachEvidence).filter(AgentReachEvidence.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(ResearchMemory).filter(ResearchMemory.project_id == self.project_id).delete(synchronize_session=False)
            elif stage_name == "graph":
                self.db.query(KnowledgeEdge).filter(KnowledgeEdge.project_id == self.project_id).delete(synchronize_session=False)
                self.db.query(KnowledgeNode).filter(KnowledgeNode.project_id == self.project_id).delete(synchronize_session=False)

            # Reset the stage record state
            stage_rec = self.db.query(ResearchStage).filter(
                ResearchStage.project_id == self.project_id,
                ResearchStage.stage_name == stage_name
            ).first()
            if stage_rec:
                stage_rec.status = "pending"
                stage_rec.completed_at = None
                stage_rec.output_data = None
                stage_rec.is_approved = False

            self.db.commit()
        except Exception as e:
            logger.warning(f"Saga cleanup for stage '{stage_name}' encountered warning: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    async def _execute_stage(
        self, 
        stage_name: str, 
        agent_fn=None, 
        resume: bool = False, 
        runner_fn=None, 
        *args, 
        **kwargs
    ):
        """
        Executes a single pipeline stage with strict unit-of-work semantics:
        1. Checks for checkpoint resumption;
        2. Compensates/purges partial stage artifacts before execution;
        3. Updates stage status and project checkpoint;
        4. Rolls back and marks stage as failed on unhandled errors.
        """
        self._update_checkpoint(stage_name)
        done, existing_results = self._is_stage_completed(stage_name)
        if resume and done:
            self.log(f"[CHECKPOINT RESUME] Stage '{stage_name}' already completed. Skipping to next stage.")
            return existing_results

        # Saga pattern: compensating cleanup of previous partial artifacts for this stage
        self._clean_stage_artifacts(stage_name)

        try:
            if runner_fn:
                results = await runner_fn()
            else:
                agent = agent_fn()
                if hasattr(agent, "on_log_callback"):
                    agent.on_log_callback = self._on_agent_log
                if hasattr(agent, "on_reasoning_callback"):
                    agent.on_reasoning_callback = self._on_agent_reasoning
                results = await agent.execute(*args, **kwargs)
            return results
        except Exception as exc:
            logger.error(f"Stage '{stage_name}' failed for project {self.project_id}: {exc}", exc_info=True)
            try:
                self.db.rollback()
            except Exception:
                pass
            # Mark stage as failed in research_stages table
            try:
                stage = self.db.query(ResearchStage).filter(
                    ResearchStage.project_id == self.project_id,
                    ResearchStage.stage_name == stage_name
                ).first()
                if stage:
                    stage.status = "failed"
                    stage.user_feedback = f"Execution error: {str(exc)}"
                    self.db.commit()
            except Exception:
                pass
            raise exc

    def _is_stage_completed(self, stage_name: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if stage was already completed in this project to enable zero-loss resumption."""
        stage = self.db.query(ResearchStage).filter(
            ResearchStage.project_id == self.project_id,
            ResearchStage.stage_name == stage_name
        ).first()
        if stage and stage.status == "completed" and stage.output_data:
            return True, stage.output_data
        return False, None

    async def run_pipeline(self, topic: str, resume: bool = False):
        """
        Execute the full 13-stage AI Scientist research pipeline with automatic
        stage checkpointing, heartbeat updates, saga compensations, and zero-loss crash resumption.
        """
        if self.db is None:
            from app.core.database import SessionLocal
            self.db = SessionLocal()
            self._owns_session = True
            
        self._set_project_status("running")
        action_verb = "RESUMING" if resume else "INITIALIZING"
        self.log(f"=== {action_verb} RESEARCH PIPELINE FOR TOPIC: '{topic}' ===")
        
        try:
            # 1. Literature Review
            lit_results = await self._execute_stage(
                "literature",
                lambda: LiteratureReviewAgent(self.db, self.project_id),
                resume=resume,
                topic=topic
            )
            
            # 2. Research Gap
            gap_results = await self._execute_stage(
                "gap",
                lambda: ResearchGapAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 3. Hypothesis Generation
            hypo_results = await self._execute_stage(
                "hypothesis",
                lambda: HypothesisGeneratorAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 4. Agent Debate
            debate_results = await self._execute_stage(
                "debate",
                lambda: DebateAgent(self.db, self.project_id),
                resume=resume
            )
            
            # Wait for Hypothesis Approval (Event-driven)
            await self._wait_for_approval("debate")
            
            # 5. Dataset Discovery
            dataset_results = await self._execute_stage(
                "dataset",
                lambda: DatasetDiscoveryAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 6. Experiment Planner
            planner_results = await self._execute_stage(
                "planning",
                lambda: ExperimentPlannerAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 7. Code Generation
            codegen_results = await self._execute_stage(
                "coding",
                lambda: CodeGenerationAgent(self.db, self.project_id),
                resume=resume
            )
            
            # Wait for Code Verification (Event-driven)
            await self._wait_for_approval("coding")
            
            # 8. Experiment Execution
            execution_results = await self._execute_stage(
                "execution",
                lambda: ExperimentExecutionAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 9. Evaluation
            evaluation_results = await self._execute_stage(
                "evaluation",
                lambda: EvaluationAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 10. Scientific Writer
            writer_results = await self._execute_stage(
                "writing",
                lambda: ScientificWriterAgent(self.db, self.project_id),
                resume=resume
            )
            
            # 11. Peer Reviewer
            reviewer_results = await self._execute_stage(
                "review",
                lambda: PeerReviewerAgent(self.db, self.project_id),
                resume=resume
            )
            
            # Phase 14: Automated Manuscript Revision Loop (Max 1 cycle)
            if reviewer_results and round(float(reviewer_results.get("score", 0)), 2) < 8.5 and not (resume and self._is_stage_completed("review")[0]):
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
                codegen_results = await self._execute_stage(
                    "coding",
                    lambda: CodeGenerationAgent(self.db, self.project_id),
                    resume=False,
                    review_feedback=review_feedback
                )
                
                # Re-invoke 8. Experiment Execution
                self.log("Re-invoking Experiment Execution Agent...")
                execution_results = await self._execute_stage(
                    "execution",
                    lambda: ExperimentExecutionAgent(self.db, self.project_id),
                    resume=False
                )
                
                # Re-invoke 9. Evaluation
                self.log("Re-invoking Evaluation Agent...")
                evaluation_results = await self._execute_stage(
                    "evaluation",
                    lambda: EvaluationAgent(self.db, self.project_id),
                    resume=False
                )
                
                # Re-invoke 10. Scientific Writer (incorporating corrections)
                self.log("Re-invoking Scientific Writer Agent with reviewer feedback...")
                writer_results = await self._execute_stage(
                    "writing",
                    lambda: ScientificWriterAgent(self.db, self.project_id),
                    resume=False,
                    review_feedback=review_feedback
                )
                
                # Re-invoke 11. Peer Reviewer (re-scoring the manuscript)
                self.log("Re-invoking Peer Reviewer Agent for final scoring...")
                reviewer_results = await self._execute_stage(
                    "review",
                    lambda: PeerReviewerAgent(self.db, self.project_id),
                    resume=False
                )
                
                self.log(f"Automated revision loop completed. New score: {reviewer_results.get('score')}/10.0")
            
            # 12. Reach Layer & Memory Consolidation
            async def run_memory_stage():
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
                memory_agent.on_reasoning_callback = self._on_agent_reasoning
                return await memory_agent.execute(evaluation_results or {})

            memory_results = await self._execute_stage(
                "memory",
                resume=resume,
                runner_fn=run_memory_stage
            )
            
            # 13. Knowledge Graph Compile
            graph_results = await self._execute_stage(
                "graph",
                lambda: KnowledgeGraphAgent(self.db, self.project_id),
                resume=resume
            )
            
            self.log("=== FULL PIPELINE COMPLETED SUCCESSFULLY ===")
            self._set_project_status("completed")
            self._update_checkpoint("completed")
            
        except Exception as e:
            logger.error(f"Pipeline error on project {self.project_id}: {e}", exc_info=True)
            self.log(f"=== PIPELINE TERMINATED WITH ERROR: {e} ===", "ERROR")
            self._set_project_status("failed")
        finally:
            if self._owns_session and self.db is not None:
                self.db.close()
                self.db = None
            
    async def _wait_for_approval(self, stage_name: str):
        # Refresh DB state
        self.db.expire_all()
        stage = self.db.query(ResearchStage).filter(
            ResearchStage.project_id == self.project_id,
            ResearchStage.stage_name == stage_name
        ).first()

        # If already approved prior to resume, continue immediately without pausing
        if stage and stage.is_approved:
            self.log(f"Stage '{stage_name}' has prior approval on record. Continuing without pause...")
            return

        self.log(f"Pipeline paused. Waiting for supervisor approval on stage: '{stage_name}'...")
        if stage:
            stage.status = "paused"
            self.db.commit()
            
            # Broadcast the paused status over WebSocket
            if self.status_callback:
                self.status_callback("paused")
                
        key = (self.project_id, stage_name)
        event = asyncio.Event()
        STAGE_APPROVAL_EVENTS[key] = event
        
        try:
            while True:
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
                    
                # Wait for approval event signal or 5-second periodic check
                try:
                    await asyncio.wait_for(event.wait(), timeout=5.0)
                    event.clear()
                except asyncio.TimeoutError:
                    pass
        finally:
            STAGE_APPROVAL_EVENTS.pop(key, None)

    def _on_agent_log(self, log_entry: dict):
        if self.log_callback:
            self.log_callback(log_entry)

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "stage": "manager"
        }
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(
            f"[MANAGER - {level}] {message}",
            extra={"stage": "manager", "project_id": self.project_id}
        )
        if self.log_callback:
            self.log_callback(log_entry)
