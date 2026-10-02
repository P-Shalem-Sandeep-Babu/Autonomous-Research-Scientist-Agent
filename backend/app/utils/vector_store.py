import math
import logging
import hashlib
from typing import List, Dict, Any, Optional
from app.utils.llm import get_llm_client
from app.core.database import SessionLocal
from app.models.models import DocumentEmbedding

logger = logging.getLogger(__name__)

def _generate_dense_fallback_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Deterministic 384-dimensional subword n-gram / token semantic projection.
    Uses polynomial hash signed projection (SimHash / random-projection style)
    with L2 normalization. This ensures meaningful similarity bounds without
    collapsing or relying on naive ASCII modulo.
    """
    vector = [0.0] * dim
    clean_text = text.lower().strip()
    if not clean_text:
        return vector

    # Word tokens
    words = clean_text.split()
    for word in words:
        # Full word feature
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vector[idx] += 1.5 * sign

        # Subword character n-grams (3 to 5 grams)
        for n in range(3, min(6, len(word) + 1)):
            for i in range(len(word) - n + 1):
                gram = word[i:i + n]
                gh = int(hashlib.sha1(gram.encode("utf-8")).hexdigest(), 16)
                g_idx = gh % dim
                g_sign = 1.0 if ((gh >> 4) & 1) else -1.0
                vector[g_idx] += 0.8 * g_sign

    # L2 Normalize
    norm = math.sqrt(sum(val ** 2 for val in vector))
    if norm > 0:
        vector = [val / norm for val in vector]
    return vector


class SimpleVectorStore:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.embeddings: List[List[float]] = []
        self._load_from_db()

    def _load_from_db(self):
        """Hydrate vector store from persistent SQLite database on startup or initialization."""
        try:
            db = SessionLocal()
            try:
                records = db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.collection_name == self.collection_name
                ).all()
                self.documents = []
                self.metadatas = []
                self.ids = []
                self.embeddings = []
                for rec in records:
                    self.ids.append(rec.doc_id)
                    self.documents.append(rec.text)
                    self.metadatas.append(rec.metadata_json or {})
                    self.embeddings.append(rec.embedding_json or [])
                if records:
                    logger.info(f"Loaded {len(records)} persistent embeddings for collection '{self.collection_name}'.")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not load persistent embeddings for '{self.collection_name}': {e}")

    async def get_embedding(self, text: str) -> List[float]:
        """
        Fetch embedding from Gemini if configured.
        Retries up to 2 times on transient failures.
        Does NOT globally poison future calls on a single failure;
        falls back gracefully to 384-dimensional dense projection per request.
        """
        client = get_llm_client()
        if client:
            for model_candidate in ["models/text-embedding-004", "models/embedding-001"]:
                for attempt in range(2):
                    try:
                        result = client.embed_content(
                            model=model_candidate,
                            content=text,
                            task_type="retrieval_document"
                        )
                        if result and "embedding" in result:
                            emb = result["embedding"]
                            norm = math.sqrt(sum(v ** 2 for v in emb))
                            if norm > 0:
                                return [v / norm for v in emb]
                            return emb
                    except Exception as e:
                        logger.debug(f"Gemini embed attempt {attempt+1} on {model_candidate} failed: {e}")
                        continue

        # Fallback to high-dimensional deterministic projection
        return _generate_dense_fallback_embedding(text, dim=384)

    async def add(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Add or update documents, compute embeddings, and persist to database atomically."""
        new_embeddings = []
        for doc in documents:
            new_embeddings.append(await self.get_embedding(doc))

        # Update in-memory state
        for doc, meta, doc_id, emb in zip(documents, metadatas, ids, new_embeddings):
            if doc_id in self.ids:
                idx = self.ids.index(doc_id)
                self.documents[idx] = doc
                self.metadatas[idx] = meta
                self.embeddings[idx] = emb
            else:
                self.ids.append(doc_id)
                self.documents.append(doc)
                self.metadatas.append(meta)
                self.embeddings.append(emb)

        # Persist to SQLite
        try:
            db = SessionLocal()
            try:
                for doc, meta, doc_id, emb in zip(documents, metadatas, ids, new_embeddings):
                    existing = db.query(DocumentEmbedding).filter(
                        DocumentEmbedding.collection_name == self.collection_name,
                        DocumentEmbedding.doc_id == doc_id
                    ).first()
                    if existing:
                        existing.text = doc
                        existing.metadata_json = meta
                        existing.embedding_json = emb
                    else:
                        db.add(DocumentEmbedding(
                            collection_name=self.collection_name,
                            doc_id=doc_id,
                            text=doc,
                            metadata_json=meta,
                            embedding_json=emb
                        ))
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting document embeddings to SQLite: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Could not open database session to persist embeddings: {e}")

    async def query(self, query_text: str, n_results: int = 3) -> Dict[str, Any]:
        """Query similar documents using cosine similarity over embeddings."""
        if not self.documents:
            # Recheck DB in case documents were added by another process
            self._load_from_db()

        if not self.documents:
            return {"documents": [], "metadatas": [], "ids": [], "distances": []}

        query_vec = await self.get_embedding(query_text)
        q_len = len(query_vec)

        # Calculate cosine similarity
        scores = []
        for idx, doc_vec in enumerate(self.embeddings):
            if not doc_vec:
                continue
            # If dimensions match, compute dot product (normalized vectors)
            if len(doc_vec) == q_len:
                dot_product = sum(q * d for q, d in zip(query_vec, doc_vec))
            else:
                # Dim mismatch fallback
                min_len = min(q_len, len(doc_vec))
                dot_product = sum(query_vec[i] * doc_vec[i] for i in range(min_len))
            scores.append((dot_product, idx))

        if not scores:
            return {"documents": [], "metadatas": [], "ids": [], "distances": []}

        # Sort by similarity descending
        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:n_results]

        return {
            "documents": [self.documents[idx] for _, idx in top_results],
            "metadatas": [self.metadatas[idx] for _, idx in top_results],
            "ids": [self.ids[idx] for _, idx in top_results],
            "distances": [max(0.0, 1.0 - score) for score, _ in top_results]
        }

    def clear(self):
        """Clear memory cache and delete collection records from database."""
        self.documents = []
        self.metadatas = []
        self.ids = []
        self.embeddings = []
        try:
            db = SessionLocal()
            try:
                db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.collection_name == self.collection_name
                ).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to clear database collection '{self.collection_name}': {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Could not open database session to clear collection: {e}")


# Global store manager
_stores: Dict[str, SimpleVectorStore] = {}

def get_vector_store(collection_name: str) -> SimpleVectorStore:
    if collection_name not in _stores:
        _stores[collection_name] = SimpleVectorStore(collection_name)
    return _stores[collection_name]
