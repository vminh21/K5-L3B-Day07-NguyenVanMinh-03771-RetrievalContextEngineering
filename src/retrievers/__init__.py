"""Retrievers sharing one interface: search(query, *, filters=None, top_k=5) -> list[dict].

Each result dict has: id, text, source_id, source, page, metadata, score, rank, strategy.
"""
from src.retrievers.base import RetrievalError, load_chunks  # noqa: F401


def build(method: str, **kwargs):
    """Factory used by eval scripts and the agent: method in {dense, bm25, hybrid}."""
    if method == "dense":
        from src.retrievers.dense import DenseRetriever
        return DenseRetriever(**kwargs)
    if method == "bm25":
        from src.retrievers.bm25 import BM25Retriever
        return BM25Retriever(**kwargs)
    if method == "hybrid":
        from src.retrievers.hybrid_rrf import HybridRRFRetriever
        return HybridRRFRetriever(**kwargs)
    raise ValueError(f"unknown retrieval method: {method}")
