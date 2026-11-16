import unittest

from src.context import ContextPacker, header


def mk(i, page, n=200, rank=1):
    return {"id": f"c{i}", "text": f"Sentence {i} " + "x" * n + ". More words here. End.", "source_id": "doc",
            "source": "doc.pdf", "page": page, "metadata": {"chapter": "Chapter I"}, "rank": rank, "score": 1.0}


class TestContextPacker(unittest.TestCase):
    def test_dedup_headers_and_budget(self):
        a, b = mk(1, 3, rank=1), mk(2, 4, rank=2)
        out = ContextPacker(budget_chars=10_000).pack([[a, b], [dict(a, rank=1)]])
        self.assertEqual(out["context_ids"], ["c1", "c2"])
        self.assertEqual(out["n_candidates"], 3)
        self.assertIn(header(a), out["context_text"])
        self.assertIn("page 3 | Chapter I", out["context_text"])
        self.assertEqual(out["chars"], len(out["context_text"]))

    def test_budget_includes_headers_and_never_exceeded(self):
        hits = [mk(i, i, n=400, rank=i) for i in range(1, 6)]
        out = ContextPacker(budget_chars=1200).pack([hits])
        self.assertLessEqual(out["chars"], 1200)
        self.assertTrue(out["dropped_ids"])

    def test_interleave_second_search_not_starved(self):
        s1 = [mk(1, 1, n=500, rank=1), mk(2, 2, n=500, rank=2)]
        s2 = [mk(3, 3, n=100, rank=1)]
        out = ContextPacker(budget_chars=1000).pack([s1, s2])
        self.assertIn("c3", out["context_ids"])  # rank-1 of the 2nd search beats rank-2 of the 1st

    def test_truncate_keeps_whole_sentences(self):
        long = dict(mk(2, 2, rank=2), text="First short sentence. Second short sentence. " + "y" * 400 + ".")
        out = ContextPacker(budget_chars=300, overflow="truncate").pack([[mk(1, 1, n=50), long]])
        self.assertIn("c2", out["truncated_ids"])
        self.assertTrue(out["context_text"].endswith("[…]"))
        self.assertLessEqual(out["chars"], 300)

    def test_neighbors(self):
        chunks = [mk(1, 5, n=20), mk(2, 5, n=20), mk(3, 9, n=20)]
        out = ContextPacker(budget_chars=5000, neighbors=True, chunks=chunks).pack([[chunks[1]]])
        self.assertEqual(out["context_ids"], ["c2", "c1"])  # c3 is 4 pages away -> not a neighbor
        self.assertEqual(out["neighbor_ids"], ["c1"])


if __name__ == "__main__":
    unittest.main()
