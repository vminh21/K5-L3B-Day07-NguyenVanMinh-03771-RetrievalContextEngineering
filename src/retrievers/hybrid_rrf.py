"""M3 — Hybrid: dense + BM25 fused with Reciprocal Rank Fusion (ranks only, raw scores never added)."""
from src.retrievers.bm25 import BM25Retriever
from src.retrievers.dense import DenseRetriever


class HybridRRFRetriever:
    name = "hybrid_rrf"

    def __init__(self, dense=None, lexical=None, k: int = 60, pool: int = 20, dedup_text: bool = False):
        self.dense = dense or DenseRetriever()
        self.lexical = lexical or BM25Retriever()
        self.k, self.pool, self.dedup_text = k, pool, dedup_text
        self.params = {"rrf_k": k, "candidate_pool": pool, "components": ["dense", "bm25"], "dedup_text": dedup_text}
        if dedup_text:
            # Day 6 stored some passages twice (identical text, different IDs). Map every copy to one
            # canonical ID (smallest ID) so a passage counts once per component list.
            canon: dict[str, str] = {}
            self.canonical = {}
            for c in sorted(self.lexical.chunks, key=lambda c: c["id"]):
                key = " ".join(c["text"].split())
                self.canonical[c["id"]] = canon.setdefault(key, c["id"])
            self.by_id = {c["id"]: c for c in self.lexical.chunks}

    def _dedup(self, hits: list[dict]) -> list[dict]:
        seen, out = set(), []
        for h in hits:
            cid = self.canonical.get(h["id"], h["id"])
            if cid in seen:
                continue
            seen.add(cid)
            base = self.by_id[cid] if cid != h["id"] else h
            out.append({**base, "score": h["score"], "rank": len(out) + 1, "strategy": h["strategy"]})
        return out

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        # Errors from either component propagate (RetrievalError): no silent dense-only/bm25-only fallback.
        lists = {"dense": self.dense.search(query, filters=filters, top_k=self.pool),
                 "bm25": self.lexical.search(query, filters=filters, top_k=self.pool)}
        if self.dedup_text:
            lists = {k: self._dedup(v) for k, v in lists.items()}
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
