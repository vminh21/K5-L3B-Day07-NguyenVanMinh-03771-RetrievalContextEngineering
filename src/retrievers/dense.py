"""M1 — Dense retrieval on the Day 6 pgvector index (cosine, embeddinggemma 768-d)."""
import psycopg

from src import config
from src.retrievers.base import RetrievalError, load_chunks, result


class DenseRetriever:
    name = "dense"

    def __init__(self, embedder=None, store=None, strategy: str | None = None, chunks=None):
        self.strategy = strategy or config.DAY6_STRATEGY
        try:
            if embedder is None:
                from src.embeddings import MyEmbedder
                embedder = MyEmbedder(model_name=config.EMBEDDING_MODEL, base_url=config.OLLAMA_BASE_URL)
            if store is None:
                from src.store import PgVectorStore
                store = PgVectorStore(config.DATABASE_URL, dimensions=embedder.dimensions)
        except RuntimeError as e:  # Ollama unreachable while probing dimensions
            raise RetrievalError(f"dense init failed: {e}") from e
        self.embedder, self.store = embedder, store
        # canonical chunk records (portable `source`) keyed by ID, so all methods return identical fields
        self.by_id = {c["id"]: c for c in (chunks if chunks is not None else load_chunks())}
        self.params = {"strategy": self.strategy, "embedding": getattr(embedder, "model_name", "?"),
                       "dimensions": getattr(embedder, "dimensions", None), "metric": "cosine"}

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        try:
            vec = self.embedder.embed_query(query)
        except RuntimeError as e:
            raise RetrievalError(f"embedding failed (Ollama): {e}") from e
        try:
            rows = self.store.search(self.strategy, vec, top_k=top_k, filters=filters)
        except psycopg.Error as e:
            raise RetrievalError(f"pgvector query failed: {e}") from e
        out = []
        for i, r in enumerate(rows, 1):
            chunk = self.by_id.get(r["chunk_id"])
            if chunk is None:
                raise RetrievalError(f"chunk {r['chunk_id']} is in pgvector but not in chunks.json — re-run export")
            out.append(result(chunk, r["score"], i, self.name))
        return out
