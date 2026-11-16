"""Unit tests for the Day 7 retrievers. Mocks are used ONLY here (never for benchmark results)."""
import unittest

import psycopg

from src.retrievers.base import RetrievalError, matches
from src.retrievers.bm25 import BM25Retriever, tokenize
from src.retrievers.dense import DenseRetriever
from src.retrievers.hybrid_rrf import HybridRRFRetriever

CHUNKS = [
    {"id": "c1", "text": "The history of all hitherto existing society is the history of class struggles.",
     "source_id": "doc", "source": "doc.pdf", "page": 3, "metadata": {"chapter": "Chapter I"}},
    {"id": "c2", "text": "The Communists disdain to conceal their views and aims.",
     "source_id": "doc", "source": "doc.pdf", "page": 33, "metadata": {"chapter": "Chapter IV"}},
    {"id": "c3", "text": "Abolition of property in land and application of all rents of land to public purposes.",
     "source_id": "doc", "source": "doc.pdf", "page": 21, "metadata": {"chapter": "Chapter II"}},
]
KEYS = {"id", "text", "source_id", "source", "page", "metadata", "score", "rank", "strategy"}


class FakeEmbedder:
    model_name, dimensions = "fake", 3

    def __init__(self, fail=False):
        self.fail = fail

    def embed_query(self, q):
        if self.fail:
            raise RuntimeError("Ollama connection failed")
        return [0.1, 0.2, 0.3]


class FakeStore:
    def __init__(self, rows=None, fail=False):
        self.rows, self.fail, self.calls = rows or [], fail, []

    def search(self, strategy, vec, top_k=3, filters=None):
        self.calls.append((strategy, top_k, filters))
        if self.fail:
            raise psycopg.OperationalError("connection refused")
        return self.rows[:top_k]


class TestBM25(unittest.TestCase):
    def test_tokenize_drops_stopwords(self):
        self.assertEqual(tokenize("The history of Class struggles"), ["history", "class", "struggles"])

    def test_search_format_rank_and_filter(self):
        r = BM25Retriever(chunks=CHUNKS)
        hits = r.search("history of class struggles", top_k=3)
        self.assertEqual(hits[0]["id"], "c1")
        self.assertTrue(KEYS <= set(hits[0]))
        self.assertEqual([h["rank"] for h in hits], list(range(1, len(hits) + 1)))
        self.assertEqual(r.search("history class", filters={"chapter": "Chapter II"}), [])

    def test_empty_query(self):
        self.assertEqual(BM25Retriever(chunks=CHUNKS).search("the of and"), [])


class TestDense(unittest.TestCase):
    def test_maps_rows_to_canonical_chunks(self):
        store = FakeStore([{"chunk_id": "c2", "score": 0.9}, {"chunk_id": "c1", "score": 0.5}])
        r = DenseRetriever(embedder=FakeEmbedder(), store=store, strategy="B", chunks=CHUNKS)
        hits = r.search("views and aims", filters={"chapter": "Chapter IV"}, top_k=2)
        self.assertEqual([h["id"] for h in hits], ["c2", "c1"])
        self.assertEqual(hits[0]["source"], "doc.pdf")
        self.assertEqual(store.calls[0], ("B", 2, {"chapter": "Chapter IV"}))

    def test_errors_are_explicit(self):
        r = DenseRetriever(embedder=FakeEmbedder(fail=True), store=FakeStore(), chunks=CHUNKS)
        with self.assertRaises(RetrievalError):
            r.search("x")
        r = DenseRetriever(embedder=FakeEmbedder(), store=FakeStore(fail=True), chunks=CHUNKS)
        with self.assertRaises(RetrievalError):
            r.search("x")

    def test_unknown_chunk_id_is_an_error(self):
        r = DenseRetriever(embedder=FakeEmbedder(), store=FakeStore([{"chunk_id": "zz", "score": 1}]), chunks=CHUNKS)
        with self.assertRaises(RetrievalError):
            r.search("x")


class TestHybrid(unittest.TestCase):
    def test_rrf_uses_ranks_not_raw_scores(self):
        # dense ranks c2 first with a tiny score; bm25 ranks c1 first with a huge score.
        dense = DenseRetriever(embedder=FakeEmbedder(), chunks=CHUNKS,
                               store=FakeStore([{"chunk_id": "c3", "score": 0.01}, {"chunk_id": "c1", "score": 0.009}]))
        h = HybridRRFRetriever(dense=dense, lexical=BM25Retriever(chunks=CHUNKS), k=60, pool=5)
        hits = h.search("history class struggles", top_k=3)
        self.assertEqual(hits[0]["id"], "c1")  # in both lists -> highest fused score
        self.assertAlmostEqual(hits[0]["score"], 1 / 62 + 1 / 61)
        self.assertEqual(hits[0]["component_ranks"], {"dense": 2, "bm25": 1})

    def test_component_failure_propagates(self):
        dense = DenseRetriever(embedder=FakeEmbedder(), store=FakeStore(fail=True), chunks=CHUNKS)
        with self.assertRaises(RetrievalError):
            HybridRRFRetriever(dense=dense, lexical=BM25Retriever(chunks=CHUNKS)).search("history")


class TestFilter(unittest.TestCase):
    def test_matches(self):
        self.assertTrue(matches(CHUNKS[0], None))
        self.assertTrue(matches(CHUNKS[0], {"chapter": "Chapter I", "section": None}))
        self.assertFalse(matches(CHUNKS[0], {"chapter": "Chapter II"}))



class TestHybridDedup(unittest.TestCase):
    def test_identical_text_counted_once(self):
        dup = dict(CHUNKS[0], id="c1b")  # same text as c1, different ID (Day 6 duplicate)
        chunks = CHUNKS + [dup]
        dense = DenseRetriever(embedder=FakeEmbedder(), chunks=chunks,
                               store=FakeStore([{"chunk_id": "c1b", "score": 0.9}, {"chunk_id": "c1", "score": 0.9},
                                                {"chunk_id": "c3", "score": 0.5}]))
        h = HybridRRFRetriever(dense=dense, lexical=BM25Retriever(chunks=chunks), dedup_text=True, pool=5)
        ids = [x["id"] for x in h.search("history class struggles", top_k=5)]
        self.assertEqual(ids.count("c1") + ids.count("c1b"), 1)
        self.assertIn("c1", ids)  # canonical = smallest ID


if __name__ == "__main__":
    unittest.main()
