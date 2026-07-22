import json
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.utils.llm import generate_text
from app.models.models import ResearchMemory, LiteraturePaper, Hypothesis, ExperimentRun, Project


class MemoryAgent(BaseAgent):
    def __init__(self, db: Session, project_id: int):
        super().__init__(db, project_id, "memory")
        self.on_log_callback = None

    async def execute(self, findings: dict) -> dict:
        """
        Derive memories directly from the research paper content and pipeline results.
        Nothing is hardcoded — every insight comes from what was extracted/run.
        """
        self.start_stage()
        try:
            self.log("Consolidating research findings into long-term system memory...")

            # ── Pull context from the pipeline ────────────────────────────────
            project = self.db.query(Project).get(self.project_id)
            topic = project.title if project else "research"

            # Top literature paper (preferring uploaded/local reference)
            papers = self.db.query(LiteraturePaper).filter(
                LiteraturePaper.project_id == self.project_id
            ).order_by(LiteraturePaper.relevance_score.desc()).all()

            local_papers = [p for p in papers if "local reference" in (p.source or "").lower()]
            top_paper = local_papers[0] if local_papers else (papers[0] if papers else None)

            # Selected hypothesis
            selected_hypo = self.db.query(Hypothesis).filter(
                Hypothesis.project_id == self.project_id,
                Hypothesis.selected == True
            ).first()

            # Latest experiment run
            run = self.db.query(ExperimentRun).filter(
                ExperimentRun.project_id == self.project_id
            ).order_by(ExperimentRun.created_at.desc()).first()

            # ── Build memories from actual content ────────────────────────────
            memories_to_save = []

            # Memory 1 – Successful method from paper
            if top_paper and top_paper.methodology:
                memories_to_save.append({
                    "memory_type": "successful_method",
                    "key": f"method_{self.project_id}_{topic[:30].replace(' ', '_').lower()}",
                    "value": {
                        "description": top_paper.methodology[:500],
                        "source_paper": top_paper.title[:150],
                        "topic": topic
                    }
                })

            # Memory 2 – Key finding from paper
            if top_paper and top_paper.findings:
                memories_to_save.append({
                    "memory_type": "key_insight",
                    "key": f"finding_{self.project_id}_{topic[:30].replace(' ', '_').lower()}",
                    "value": {
                        "description": top_paper.findings[:500],
                        "source_paper": top_paper.title[:150],
                        "topic": topic
                    }
                })

            # Memory 3 – Limitation / failed method from paper
            if top_paper and top_paper.limitations:
                memories_to_save.append({
                    "memory_type": "failed_method",
                    "key": f"limitation_{self.project_id}_{topic[:30].replace(' ', '_').lower()}",
                    "value": {
                        "description": top_paper.limitations[:500],
                        "source_paper": top_paper.title[:150],
                        "topic": topic
                    }
                })

            # Memory 4 – Selected hypothesis
            if selected_hypo:
                memories_to_save.append({
                    "memory_type": "key_insight",
                    "key": f"hypothesis_{self.project_id}",
                    "value": {
                        "description": selected_hypo.statement[:400],
                        "reasoning": (selected_hypo.reasoning or "")[:300],
                        "confidence": selected_hypo.confidence_level,
                        "topic": topic
                    }
                })

            # Memory 5 – Experiment results
            if run and run.metrics_history:
                last = run.metrics_history[-1]
                metrics_str = json.dumps(last)
                memories_to_save.append({
                    "memory_type": "successful_method",
                    "key": f"experiment_result_{self.project_id}",
                    "value": {
                        "description": f"Final metrics for '{topic}': {metrics_str}",
                        "topic": topic
                    }
                })

            # ── Fallback if nothing was extracted ─────────────────────────────
            if not memories_to_save:
                memories_to_save.append({
                    "memory_type": "key_insight",
                    "key": f"pipeline_completed_{self.project_id}",
                    "value": {
                        "description": f"Research pipeline completed for topic: {topic}. No paper uploaded.",
                        "topic": topic
                    }
                })

            # ── Persist to DB and vector store ────────────────────────────────
            saved_count = 0
            docs, metadatas, ids = [], [], []

            for mem in memories_to_save:
                existing = self.db.query(ResearchMemory).filter(
                    ResearchMemory.project_id == self.project_id,
                    ResearchMemory.key == mem["key"]
                ).first()
                if not existing:
                    memory_db = ResearchMemory(
                        project_id=self.project_id,
                        memory_type=mem["memory_type"],
                        key=mem["key"],
                        value=mem["value"]
                    )
                    self.db.add(memory_db)
                    saved_count += 1

                desc = mem["value"].get("description", "")
                docs.append(f"[{mem['memory_type'].upper()}] Key: {mem['key']}. Description: {desc}")
                metadatas.append({
                    "project_id": self.project_id,
                    "memory_type": mem["memory_type"],
                    "key": mem["key"],
                    "value_json": json.dumps(mem["value"])
                })
                ids.append(f"mem-proj-{self.project_id}-{mem['key']}")

            self.db.commit()

            try:
                from app.utils.vector_store import get_vector_store
                global_store = get_vector_store("arsa_global_memory")
                await global_store.add(documents=docs, metadatas=metadatas, ids=ids)
                self.log(f"Indexed {len(docs)} memories into global vector store.")
            except Exception as e:
                self.log(f"Vector store indexing failed: {e}", "WARNING")

            self.log(f"Persisted {saved_count} paper-derived insights to memory index.")

            output = {
                "memories_saved": saved_count,
                "insights": [m["key"] for m in memories_to_save]
            }
            self.complete_stage(output)
            return output

        except Exception as e:
            self.fail_stage(str(e))
            raise e

    async def retrieve_memories(self, query: str) -> list:
        """Fetch relevant past memories to guide new research starts."""
        results = []
        try:
            from app.utils.vector_store import get_vector_store
            global_store = get_vector_store("arsa_global_memory")

            # Auto-sync any DB memories not yet in vector store
            try:
                all_mems = self.db.query(ResearchMemory).all()
                if all_mems:
                    indexed_keys = set()
                    for doc_id in global_store.ids:
                        if doc_id.startswith("mem-proj-"):
                            indexed_keys.add("-".join(doc_id.split("-")[3:]))
                    docs, metadatas, ids = [], [], []
                    for mem in all_mems:
                        if mem.key not in indexed_keys:
                            desc = mem.value.get("description", "") if isinstance(mem.value, dict) else ""
                            docs.append(f"[{mem.memory_type.upper()}] Key: {mem.key}. {desc}")
                            metadatas.append({
                                "project_id": mem.project_id,
                                "memory_type": mem.memory_type,
                                "key": mem.key,
                                "value_json": json.dumps(mem.value)
                            })
                            ids.append(f"mem-proj-{mem.project_id}-{mem.key}")
                    if docs:
                        await global_store.add(documents=docs, metadatas=metadatas, ids=ids)
            except Exception as sync_err:
                print(f"Memory auto-sync failed: {sync_err}")

            query_results = await global_store.query(query, n_results=5)
            if query_results and "metadatas" in query_results:
                for meta in query_results["metadatas"]:
                    try:
                        val = json.loads(meta.get("value_json", "{}"))
                    except Exception:
                        val = {}
                    results.append({
                        "project_id": meta.get("project_id"),
                        "type": meta.get("memory_type"),
                        "key": meta.get("key"),
                        "value": val
                    })
        except Exception as e:
            print(f"Vector search failed, falling back to DB scan: {e}")

        if not results:
            mems = self.db.query(ResearchMemory).all()
            for m in mems:
                if query.lower() in m.key.lower() or query.lower() in str(m.value).lower():
                    results.append({
                        "project_id": m.project_id,
                        "type": m.memory_type,
                        "key": m.key,
                        "value": m.value
                    })
        return results
