import json
import httpx
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.utils.llm import generate_text
from app.models.models import Hypothesis, DatasetRecommendation, KnowledgeNode, KnowledgeEdge

class DatasetDiscoveryAgent(BaseAgent):
    def __init__(self, db: Session, project_id: int):
        super().__init__(db, project_id, "dataset")
        self.on_log_callback = None

    async def execute(self) -> dict:
        self.start_stage()
        try:
            # Get the selected hypothesis
            selected_hypo = self.db.query(Hypothesis).filter(
                Hypothesis.project_id == self.project_id,
                Hypothesis.selected == True
            ).first()
            
            hypo_stmt = selected_hypo.statement if selected_hypo else "brain tumor classification"
            self.log(f"Searching dataset repositories for hypothesis: '{hypo_stmt[:70]}...'")
            
            # Fetch papers to guide dataset suggestions
            from app.models.models import LiteraturePaper, Project
            papers = self.db.query(LiteraturePaper).filter(
                LiteraturePaper.project_id == self.project_id
            ).order_by(LiteraturePaper.relevance_score.desc()).limit(2).all()
            
            project = self.db.query(Project).get(self.project_id)
            topic = project.title if project else hypo_stmt
            
            papers_dataset_hints = ""
            if papers:
                papers_dataset_hints = "\n\n**Datasets referenced or suggested in these research papers:**\n"
                for p in papers:
                    papers_dataset_hints += (
                        f"- Paper: {p.title}\n"
                        f"  Methodology used: {p.methodology}\n"
                        f"  Abstract excerpt: {(p.abstract or '')[:400]}\n"
                    )
                papers_dataset_hints += "\nPrioritize recommending the same or directly related datasets used in these papers.\n"
            hf_datasets = []
            try:
                # Check if GNN project
                from app.models.models import UploadedPaper
                uploaded = self.db.query(UploadedPaper).filter(UploadedPaper.project_id == self.project_id).first()
                if uploaded:
                    paper_text = uploaded.content_text.lower()
                    is_gnn = any(w in paper_text for w in ["gnn", "drug", "protein", "chemical", "molecule"])
                else:
                    is_gnn = any(w in hypo_stmt.lower() for w in ["gnn", "drug", "alzheimer", "folding", "protein", "chemical", "molecule"])
                search_term = "molecule" if is_gnn else "mri"
                if not is_gnn and "mri" not in hypo_stmt.lower():
                    search_term = "medical-image"
                url = f"https://huggingface.co/api/datasets?search={search_term}&limit=3"
                self.log(f"Querying Hugging Face Datasets Hub for search term '{search_term}'...")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data[:2]:
                            hf_datasets.append({
                                "name": f"HuggingFace: {item.get('id')}",
                                "source": "Hugging Face Hub",
                                "url": f"https://huggingface.co/datasets/{item.get('id')}",
                                "quality_score": 90.0 if item.get("downloads", 0) > 100 else 80.0,
                                "description": f"Public Hugging Face repository. Downloads: {item.get('downloads', 0)}. Likes: {item.get('likes', 0)}.",
                                "metadata_fields": {
                                    "dataset_id": item.get("id"),
                                    "downloads": item.get("downloads", 0),
                                    "author": item.get("author", "unknown"),
                                    "tags": ", ".join(item.get("tags", [])[:4])
                                }
                            })
            except Exception as e:
                self.log(f"Hugging Face search skipped or failed: {e}", "WARNING")

            # Catalog datasets
            from app.models.models import UploadedPaper
            uploaded = self.db.query(UploadedPaper).filter(UploadedPaper.project_id == self.project_id).first()
            if uploaded:
                paper_text = uploaded.content_text.lower()
                is_gnn = any(w in paper_text for w in ["gnn", "drug", "protein", "chemical", "molecule"])
            else:
                is_gnn = any(w in hypo_stmt.lower() for w in ["gnn", "drug", "alzheimer", "folding", "protein", "chemical", "molecule"])
            prompt = (
                f"Topic: '{topic}'\n"
                f"Hypothesis: {hypo_stmt}\n"
                f"{papers_dataset_hints}\n"
                f"Identify public scientific datasets related to validating this hypothesis.\n"
                f"Find 2 specific benchmark datasets (e.g., {'PDBbind, MoleculeNet BACE1' if is_gnn else 'BraTS, TCGA-LGG'}).\n"
                f"**CRITICAL: If the research papers above mention specific datasets, prioritize recommending those exact datasets.**\n"
                f"For each dataset, provide name, source, url, quality_score (0-100), description, and metadata fields (instances count, modalities, annotations).\n"
                f"Respond strictly in JSON format with a list under key 'datasets'."
            )
            
            llm_response = await generate_text(prompt, system_instruction="Find and catalog relevant research datasets.")
            try:
                clean = llm_response.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[-1]
                    clean = clean.rsplit("```", 1)[0]
                dataset_data = json.loads(clean)
                llm_list = dataset_data.get("datasets", [])
            except Exception:
                if is_gnn:
                    llm_list = [
                        {
                            "name": "MoleculeNet BACE1 Inhibitors",
                            "source": "MoleculeNet / Hugging Face",
                            "url": "https://huggingface.co/datasets/MoleculeNet/bace",
                            "quality_score": 91.0,
                            "description": "Benchmark biochemical assay dataset containing 2D molecular structures (SMILES) and binding affinity values against human BACE1.",
                            "metadata_fields": {"instances": 1513, "modalities": "SMILES molecular graphs", "annotations": "Binding affinity values (IC50)"}
                        }
                    ]
                else:
                    llm_list = [
                        {
                            "name": "BraTS 2024 (Brain Tumor Segmentation)",
                            "source": "Synapse / Kaggle",
                            "url": "https://www.synapse.org/brats",
                            "quality_score": 96.0,
                            "description": "Benchmark brain tumor segmentation dataset containing multi-modal MRI scans with voxel-level segmentations.",
                            "metadata_fields": {"instances": 2000, "modalities": "T1, T1c, T2, FLAIR", "annotations": "Voxel segmentation"}
                        }
                    ]
            
            # Combine real HF datasets with LLM benchmark datasets
            combined_list = hf_datasets + llm_list
            saved_datasets = []
            
            for i, ds_entry in enumerate(combined_list):
                self.log(f"Dataset Cataloged: '{ds_entry['name']}' (Quality Score: {ds_entry['quality_score']})")
                
                ds_db = DatasetRecommendation(
                    project_id=self.project_id,
                    name=ds_entry["name"],
                    source=ds_entry["source"],
                    url=ds_entry["url"],
                    quality_score=ds_entry["quality_score"],
                    description=ds_entry["description"],
                    metadata_fields=ds_entry["metadata_fields"]
                )
                self.db.add(ds_db)
                self.db.commit()
                self.db.refresh(ds_db)
                saved_datasets.append(ds_db)
                
                # Knowledge Graph node
                ds_node_id = f"dataset-{ds_db.id}"
                node = KnowledgeNode(
                    id=ds_node_id,
                    project_id=self.project_id,
                    type="dataset",
                    label=ds_db.name[:40],
                    properties={
                        "name": ds_db.name,
                        "source": ds_db.source,
                        "quality_score": ds_db.quality_score,
                        "url": ds_db.url
                    }
                )
                self.db.merge(node)
                self.db.commit()
                
                # Link dataset to selected hypothesis
                if selected_hypo:
                    edge = KnowledgeEdge(
                        project_id=self.project_id,
                        source=ds_node_id,
                        target=f"hypothesis-{selected_hypo.id}",
                        type="validates"
                    )
                    self.db.add(edge)
                    self.db.commit()
                    
            output = {
                "datasets_found": len(saved_datasets),
                "datasets": [
                    {"id": d.id, "name": d.name, "source": d.source, "quality_score": d.quality_score, "url": d.url}
                    for d in saved_datasets
                ]
            }
            self.complete_stage(output)
            return output
            
        except Exception as e:
            self.fail_stage(str(e))
            raise e
