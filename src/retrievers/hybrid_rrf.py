"""M3 — Hybrid: dense + BM25 fused with Reciprocal Rank Fusion (ranks only, raw scores never added)."""
from src.retrievers.bm25 import BM25Retriever
from src.retrievers.dense import DenseRetriever


class HybridRRFRetriever:
    name = "hybrid_rrf"

    def __init__(self, dense=None, lexical=None, k: int = 60, pool: int = 20):
        self.dense = dense or DenseRetriever()
        self.lexical = lexical or BM25Retriever()
        self.k, self.pool = k, pool
        self.params = {"rrf_k": k, "candidate_pool": pool, "components": ["dense", "bm25"]}

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        # Errors from either component propagate (RetrievalError): no silent dense-only/bm25-only fallback.
        lists = {"dense": self.dense.search(query, filters=filters, top_k=self.pool),
                 "bm25": self.lexical.search(query, filters=filters, top_k=self.pool)}
        fused: dict[str, dict] = {}
        for comp, hits in lists.items():
            for h in hits:
                e = fused.setdefault(h["id"], {"chunk": h, "score": 0.0, "component_ranks": {}})
                e["score"] += 1.0 / (self.k + h["rank"])
                e["component_ranks"][comp] = h["rank"]
        ordered = sorted(fused.values(), key=lambda e: (-e["score"], e["chunk"]["id"]))[:top_k]
        out = []
        for r, e in enumerate(ordered, 1):
            h = {k: v for k, v in e["chunk"].items() if k not in ("score", "rank", "strategy")}
            out.append({**h, "score": e["score"], "rank": r, "strategy": self.name,
                        "component_ranks": e["component_ranks"]})
        return out
