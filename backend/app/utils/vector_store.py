import math
from typing import List, Dict, Any, Optional
from app.utils.llm import get_llm_client

class SimpleVectorStore:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.embeddings: List[List[float]] = []

    async def get_embedding(self, text: str) -> List[float]:
        """Fetch embedding from Gemini if API is configured, otherwise fallback to simple hashing/char vectors."""
        client = get_llm_client()
        if client:
            try:
                # Use Gemini Embeddings API
                model = "models/text-embedding-004"
                result = client.embed_content(
                    model=model,
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            except Exception as e:
                print(f"Error getting Gemini embedding: {e}")
        
        # Fallback keyword representation (char-based hash vector of size 128)
        vector = [0.0] * 128
        words = text.lower().split()
        for word in words:
            for char in word:
                idx = ord(char) % 128
                vector[idx] += 1.0
        
        # L2 Normalize
        norm = math.sqrt(sum(val ** 2 for val in vector))
        if norm > 0:
            vector = [val / norm for val in vector]
        return vector

    async def add(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        for doc, meta, doc_id in zip(documents, metadatas, ids):
            if doc_id in self.ids:
                idx = self.ids.index(doc_id)
                self.documents[idx] = doc
                self.metadatas[idx] = meta
                self.embeddings[idx] = await self.get_embedding(doc)
            else:
                self.documents.append(doc)
                self.metadatas.append(meta)
                self.ids.append(doc_id)
                self.embeddings.append(await self.get_embedding(doc))

    async def query(self, query_text: str, n_results: int = 3) -> Dict[str, Any]:
        if not self.documents:
            return {"documents": [], "metadatas": [], "ids": [], "distances": []}
            
        query_vec = await self.get_embedding(query_text)
        
        # Calculate cosine similarity
        scores = []
        for idx, doc_vec in enumerate(self.embeddings):
            # Cosine similarity: (A . B) / (||A|| ||B||)
            # Since vectors are normalized, it is just A . B
            dot_product = sum(q * d for q, d in zip(query_vec, doc_vec))
            scores.append((dot_product, idx))
            
        # Sort by similarity descending
        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:n_results]
        
        res = {
            "documents": [self.documents[idx] for _, idx in top_results],
            "metadatas": [self.metadatas[idx] for _, idx in top_results],
            "ids": [self.ids[idx] for _, idx in top_results],
            "distances": [1.0 - score for score, _ in top_results]  # Cosine distance
        }
        return res

# Global store manager
_stores: Dict[str, SimpleVectorStore] = {}

def get_vector_store(collection_name: str) -> SimpleVectorStore:
    if collection_name not in _stores:
        _stores[collection_name] = SimpleVectorStore(collection_name)
    return _stores[collection_name]
