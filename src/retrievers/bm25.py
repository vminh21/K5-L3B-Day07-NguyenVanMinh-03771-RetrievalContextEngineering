"""M2 — Lexical BM25 (Okapi) over data/day7/chunks.json, same chunk IDs as the dense index."""
import re
import time

from rank_bm25 import BM25Okapi

from src.retrievers.base import load_chunks, matches, result

# Small English stopword list (kept in code so results are reproducible without NLTK downloads).
STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from had has have he her his how i if in
into is it its may might more most must no not of on or our over shall she should so such than that
the their them then there these they this those to too under up upon was we were what when where which
while who whom why will with would you your according does did per
""".split())
TOKEN = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")


def tokenize(text: str) -> list[str]:
    toks = (t.replace("’", "'") for t in TOKEN.findall(text.lower()))
    return [t for t in toks if t not in STOPWORDS]


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks=None, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks if chunks is not None else load_chunks()
        t0 = time.perf_counter()
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks], k1=k1, b=b)
        self.index_seconds = time.perf_counter() - t0
        self.params = {"k1": k1, "b": b, "tokenizer": "lowercase alnum + English stopwords, no stemming",
                       "n_chunks": len(self.chunks)}

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        q = tokenize(query)
        if not q:
            return []
        scores = self.bm25.get_scores(q)
        idx = [i for i, c in enumerate(self.chunks) if matches(c, filters) and scores[i] > 0]
        idx.sort(key=lambda i: (-scores[i], self.chunks[i]["id"]))
        return [result(self.chunks[i], scores[i], r, self.name) for r, i in enumerate(idx[:top_k], 1)]
