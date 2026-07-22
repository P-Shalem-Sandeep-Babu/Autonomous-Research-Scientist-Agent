from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.models.models import (
    KnowledgeNode, KnowledgeEdge, ScientificPaper, PeerReview,
    LiteraturePaper, ResearchGap, Hypothesis, GeneratedFile
)


class KnowledgeGraphAgent(BaseAgent):
    def __init__(self, db: Session, project_id: int):
        super().__init__(db, project_id, "graph")
        self.on_log_callback = None

    def _safe_add_edge(self, source: str, target: str, edge_type: str):
        """Add an edge only if both source and target nodes exist."""
        src_exists = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == source,
            KnowledgeNode.project_id == self.project_id
        ).first()
        tgt_exists = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == target,
            KnowledgeNode.project_id == self.project_id
        ).first()
        if src_exists and tgt_exists:
            # Avoid duplicate edges
            dup = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.project_id == self.project_id,
                KnowledgeEdge.source == source,
                KnowledgeEdge.target == target,
                KnowledgeEdge.type == edge_type
            ).first()
            if not dup:
                self.db.add(KnowledgeEdge(
                    project_id=self.project_id,
                    source=source,
                    target=target,
                    type=edge_type
                ))

    async def execute(self) -> dict:
        self.start_stage()
        try:
            self.log("Compiling full research knowledge graph from all pipeline outputs...")

            # ── 1. Add/update nodes for uploaded / local reference papers ─────
            local_papers = self.db.query(LiteraturePaper).filter(
                LiteraturePaper.project_id == self.project_id,
                LiteraturePaper.source == "Local Reference Library"
            ).all()

            for lp in local_papers:
                node_id = f"paper-{lp.id}"
                node = KnowledgeNode(
                    id=node_id,
                    project_id=self.project_id,
                    type="uploaded_paper",
                    label=(lp.title[:40] + "..."),
                    properties={
                        "title": lp.title,
                        "source": lp.source,
                        "methodology": (lp.methodology or "")[:200],
                        "findings": (lp.findings or "")[:200],
                        "limitations": (lp.limitations or "")[:200],
                        "relevance_score": lp.relevance_score
                    }
                )
                self.db.merge(node)
            self.db.commit()
            self.log(f"Registered {len(local_papers)} uploaded reference paper nodes.")

            # ── 2. Link: uploaded paper → gaps that arise from it ─────────────
            gaps = self.db.query(ResearchGap).filter(
                ResearchGap.project_id == self.project_id
            ).all()
            for gap in gaps:
                gap_node_id = f"gap-{gap.id}"
                for lp in local_papers:
                    self._safe_add_edge(gap_node_id, f"paper-{lp.id}", "arises_from")
            self.db.commit()

            # ── 3. Link: hypotheses → gaps ────────────────────────────────────
            hypotheses = self.db.query(Hypothesis).filter(
                Hypothesis.project_id == self.project_id
            ).all()
            for hypo in hypotheses:
                hypo_node_id = f"hypothesis-{hypo.id}"
                for gap in gaps:
                    self._safe_add_edge(hypo_node_id, f"gap-{gap.id}", "addresses")
            self.db.commit()

            # ── 4. Add paper draft node and link everything to it ─────────────
            latest_paper = self.db.query(ScientificPaper).filter(
                ScientificPaper.project_id == self.project_id
            ).order_by(ScientificPaper.created_at.desc()).first()

            if latest_paper:
                paper_draft_id = f"paper-draft-{latest_paper.id}"
                self.db.merge(KnowledgeNode(
                    id=paper_draft_id,
                    project_id=self.project_id,
                    type="paper_draft",
                    label=(latest_paper.title[:35] + "..."),
                    properties={
                        "title": latest_paper.title,
                        "readiness_score": latest_paper.publication_readiness_score
                    }
                ))
                self.db.commit()

                # Link: selected hypothesis → draft
                selected_hypo = next((h for h in hypotheses if h.selected), None)
                if selected_hypo:
                    self._safe_add_edge(
                        f"hypothesis-{selected_hypo.id}", paper_draft_id, "supports"
                    )

                # Link: code node → draft
                code_node_id = f"code-project-{self.project_id}"
                self._safe_add_edge(code_node_id, paper_draft_id, "implements")

                # Link: uploaded papers → draft (paper extends them)
                for lp in local_papers:
                    self._safe_add_edge(paper_draft_id, f"paper-{lp.id}", "extends")

                # ── 5. Peer review node ───────────────────────────────────────
                review = self.db.query(PeerReview).filter(
                    PeerReview.paper_id == latest_paper.id
                ).first()
                if review:
                    review_node_id = f"review-{review.id}"
                    self.db.merge(KnowledgeNode(
                        id=review_node_id,
                        project_id=self.project_id,
                        type="peer_review",
                        label=f"Review Score: {review.score}/10",
                        properties={
                            "score": review.score,
                            "suggestions_count": len(review.suggestions or [])
                        }
                    ))
                    self.db.commit()
                    self._safe_add_edge(review_node_id, paper_draft_id, "evaluates")

                self.db.commit()

            # ── 6. Final count ────────────────────────────────────────────────
            nodes = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.project_id == self.project_id
            ).all()
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.project_id == self.project_id
            ).all()

            self.log(
                f"Knowledge graph compiled: {len(nodes)} nodes, {len(edges)} edges. "
                f"Full lineage: uploaded paper → gaps → hypotheses → code → manuscript → review."
            )

            output = {
                "nodes": [
                    {"id": n.id, "type": n.type, "label": n.label, "properties": n.properties}
                    for n in nodes
                ],
                "edges": [
                    {"source": e.source, "target": e.target, "type": e.type}
                    for e in edges
                ]
            }
            self.complete_stage(output)
            return output

        except Exception as e:
            self.fail_stage(str(e))
            raise e
