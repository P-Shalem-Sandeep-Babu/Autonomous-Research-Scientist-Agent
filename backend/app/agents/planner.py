import json
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.utils.llm import generate_text
from app.models.models import Hypothesis, DatasetRecommendation, ExperimentPlan, KnowledgeNode, KnowledgeEdge

class ExperimentPlannerAgent(BaseAgent):
    def __init__(self, db: Session, project_id: int):
        super().__init__(db, project_id, "planning")
        self.on_log_callback = None

    async def execute(self) -> dict:
        self.start_stage()
        self.reason_step("Fetching selected hypothesis and dataset recommendations from database.", "thought")
        try:
            # Retrieve selected hypothesis
            selected_hypo = self.db.query(Hypothesis).filter(
                Hypothesis.project_id == self.project_id,
                Hypothesis.selected == True
            ).first()
            
            # Retrieve datasets
            datasets = self.db.query(DatasetRecommendation).filter(
                DatasetRecommendation.project_id == self.project_id
            ).all()
            
            hypo_stmt = selected_hypo.statement if selected_hypo else "brain tumor classification"
            datasets_str = ", ".join([d.name for d in datasets]) if datasets else "standard clinical scans"
            
            # Fetch literature papers to inject research context
            from app.models.models import LiteraturePaper
            papers = self.db.query(LiteraturePaper).filter(
                LiteraturePaper.project_id == self.project_id
            ).order_by(LiteraturePaper.relevance_score.desc()).limit(3).all()
            
            papers_context = ""
            if papers:
                papers_context = "\n\n**CRITICAL: Base your experimental design on these research papers:**\n"
                for p in papers:
                    papers_context += f"- Paper: {p.title}\n"
                    papers_context += f"  Methodology: {p.methodology}\n"
                    papers_context += f"  Key Findings: {p.findings}\n"
                    papers_context += f"  Limitations: {p.limitations}\n"
                papers_context += "\nYour roadmap should address the limitations and build upon the methodologies described above.\n"
            
            self.reason_step(f"Designing detailed 4-step experimental roadmap, selecting key validation metrics, and budgeting compute parameters.", "thought")
            self.log(f"Formulating experimental roadmap to test: '{hypo_stmt[:70]}...' using datasets: {datasets_str}")
            if papers:
                self.log(f"Incorporating methodologies from {len(papers)} research papers into experiment design.")
            
            prompt = (
                f"Design an experiment planning roadmap to test this hypothesis:\n"
                f"Hypothesis: {hypo_stmt}\n"
                f"Datasets: {datasets_str}\n"
                f"{papers_context}\n"
                f"Generate:\n"
                f"1. A step-by-step roadmap (list of dicts containing 'step' title and 'details').\n"
                f"2. A list of key performance metrics (e.g. Accuracy, F1-Score, sensitivity, specificity).\n"
                f"3. Hardware requirements (GPU type, CPU, RAM, expected run-time).\n"
                f"Respond strictly in JSON format with keys: 'roadmap' (list of steps), 'metrics' (list of strings), 'hardware_requirements' (dict)."
            )
            
            llm_response = await generate_text(prompt, system_instruction="Plan academic-grade scientific experiments.")
            try:
                clean = llm_response.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[-1]
                    clean = clean.rsplit("```", 1)[0]
                plan_data = json.loads(clean)
                if "roadmap" not in plan_data:
                    raise ValueError("Missing 'roadmap' key")
            except Exception:
                from app.models.models import UploadedPaper
                uploaded = self.db.query(UploadedPaper).filter(UploadedPaper.project_id == self.project_id).first()
                if uploaded:
                    paper_text = uploaded.content_text.lower()
                    is_gnn = any(w in paper_text for w in ["gnn", "drug", "protein", "chemical", "molecule"])
                else:
                    is_gnn = any(w in hypo_stmt.lower() for w in ["gnn", "drug", "alzheimer", "folding", "protein", "chemical", "molecule"])
                if is_gnn:
                    plan_data = {
                        "roadmap": [
                            {"step": "1. Data Acquisition & Pocket Subgraph Extraction", "details": "Download PDBbind/MoleculeNet datasets. Extract target protein pocket residues within 8Å of ligand binding centroid. Clean coordinate geometries."},
                            {"step": "2. Framework Setup", "details": "Configure PyTorch Geometric. Implement Dynamic Pocket-Aware EGNN architecture supporting coordinate displacement vectors."},
                            {"step": "3. Joint Regression/Classification Training", "details": "Train ligand-pocket graphs under joint MSE loss for binding affinity and BCE loss for active state prediction."},
                            {"step": "4. Scaffold Generalization Testing", "details": "Validate model on unseen Bemis-Murcko molecular scaffolds to measure out-of-distribution performance."}
                        ],
                        "metrics": ["Pearson Correlation (R)", "Spearman Correlation", "Mean Squared Error (MSE)", "Mean Absolute Error (MAE)", "Active-Binder F1-Score"],
                        "hardware_requirements": {
                            "GPU": "1x NVIDIA RTX 4090 (24GB VRAM) recommended, or RTX 3080 minimum",
                            "CPU": "8 cores AMD Ryzen / Intel Core",
                            "RAM": "32 GB",
                            "expected_runtime": "1.5 hours"
                        }
                    }
                else:
                    plan_data = {
                        "roadmap": [
                            {"step": "1. Data Acquisition & Preprocessing", "details": "Download BraTS/LGG datasets. Apply N4ITK bias correction and normalize values to [0,1]. Split data into 70/10/20 train/val/test splits."},
                            {"step": "2. Framework Setup", "details": "Configure PyTorch codebase. Implement Domain-Adversarial Vision Transformer (DA-ViT) model architecture."},
                            {"step": "3. Adversarial Training Run", "details": "Train the domain discriminator with a gradient-reversal layer at scaling lambda=0.1. Backpropagate domain loss and classification loss jointly."},
                            {"step": "4. Generalization Testing", "details": "Evaluate generalization capacity by testing the Siemens-trained model directly on the Philips LGG dataset."}
                        ],
                        "metrics": ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC", "Domain-Classifier Accuracy"],
                        "hardware_requirements": {
                            "GPU": "1x NVIDIA A100 (80GB VRAM) recommended, or RTX 3090 (24GB VRAM) minimum",
                            "CPU": "16 cores Intel/AMD",
                            "RAM": "64 GB",
                            "expected_runtime": "3.5 hours"
                        }
                    }
                
            plan_db = ExperimentPlan(
                project_id=self.project_id,
                roadmap=plan_data.get("roadmap", []),
                metrics=plan_data.get("metrics", []),
                hardware_requirements=plan_data.get("hardware_requirements", {})
            )
            self.db.add(plan_db)
            self.db.commit()
            self.db.refresh(plan_db)
            
            # Knowledge Graph node
            plan_node_id = f"plan-{plan_db.id}"
            from app.models.models import UploadedPaper
            uploaded = self.db.query(UploadedPaper).filter(UploadedPaper.project_id == self.project_id).first()
            if uploaded:
                paper_text = uploaded.content_text.lower()
                is_gnn = any(w in paper_text for w in ["gnn", "drug", "protein", "chemical", "molecule"])
            else:
                is_gnn = any(w in hypo_stmt.lower() for w in ["gnn", "drug", "alzheimer", "folding", "protein", "chemical", "molecule"])
            node = KnowledgeNode(
                id=plan_node_id,
                project_id=self.project_id,
                type="experiment",
                label="Exp Plan: GNN Molecular Affinity" if is_gnn else "Exp Plan: Invariant Representation",
                properties={
                    "metrics": plan_db.metrics,
                    "expected_runtime": plan_db.hardware_requirements.get("expected_runtime", "unknown")
                }
            )
            self.db.merge(node)
            self.db.commit()
            
            # Link plan to selected hypothesis
            if selected_hypo:
                edge = KnowledgeEdge(
                    project_id=self.project_id,
                    source=plan_node_id,
                    target=f"hypothesis-{selected_hypo.id}",
                    type="tests"
                )
                self.db.add(edge)
                self.db.commit()
                
            output = {
                "plan_id": plan_db.id,
                "roadmap": plan_db.roadmap,
                "metrics": plan_db.metrics,
                "hardware_requirements": plan_db.hardware_requirements
            }
            self.complete_stage(output)
            return output
            
        except Exception as e:
            self.fail_stage(str(e))
            raise e
