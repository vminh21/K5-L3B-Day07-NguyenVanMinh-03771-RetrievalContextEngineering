"""M4 — Hybrid RRF candidates (pool, text-deduplicated) re-ranked by a local cross-encoder.
The number of returned chunks stays top_k (default 5): reranking changes ORDER, not how many chunks.
"""
import time

from src.retrievers.hybrid_rrf import HybridRRFRetriever

MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankRetriever:
    name = "hybrid_rerank"

    def __init__(self, base=None, model: str = MODEL, pool: int = 20, dedup_text: bool = True):
        from sentence_transformers import CrossEncoder
        self.base = base or HybridRRFRetriever(dedup_text=dedup_text, pool=pool)
        self.lexical = self.base.lexical  # for index_seconds reporting
        t0 = time.perf_counter()
        self.ce = CrossEncoder(model)
        self.load_seconds = time.perf_counter() - t0
        self.pool = pool
        self.params = {**self.base.params, "reranker": model, "rerank_pool": pool}

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        cands = self.base.search(query, filters=filters, top_k=max(self.pool, top_k))
        if not cands:
            return []
        scores = self.ce.predict([(query, " ".join(c["text"].split())) for c in cands])
        order = sorted(range(len(cands)), key=lambda i: (-float(scores[i]), cands[i]["rank"]))
        out = []
        for r, i in enumerate(order[:top_k], 1):
            c = cands[i]
            out.append({**{k: v for k, v in c.items() if k not in ("score", "rank", "strategy")},
                        "score": float(scores[i]), "rank": r, "strategy": self.name, "rrf_rank": c["rank"]})
        return out
