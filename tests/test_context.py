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



class TestContinuationFirst(unittest.TestCase):
    def setUp(self):
        # reading order: c1 (cut, p21) -> c2 (its long continuation, p21) | c3 (p30) -> c4 (long, p30)
        self.chunks = [dict(mk(1, 21, n=20), text="Nevertheless, the following will be applicable:"),
                       mk(2, 21, n=900), mk(3, 30, n=600), mk(4, 30, n=900)]

    def test_cut_hit_gets_its_continuation_before_other_neighbours(self):
        hits = [dict(self.chunks[2], rank=1), dict(self.chunks[0], rank=2)]  # c3 rank 1, cut c1 rank 2
        old = ContextPacker(budget_chars=1900, neighbors=True, chunks=self.chunks).pack([hits])
        new = ContextPacker(budget_chars=1900, neighbors=True, chunks=self.chunks, continuation_first=True).pack([hits])
        self.assertIn("c4", old["context_ids"])     # old: c3's neighbour c4 is added first ...
        self.assertNotIn("c2", old["context_ids"])  # ... and the continuation of c1 no longer fits
        self.assertIn("c2", new["context_ids"])     # new: continuation of the cut chunk is kept

    def test_exclude_already_shown(self):
        out = ContextPacker(budget_chars=10_000, neighbors=True, chunks=self.chunks).pack(
            [[dict(self.chunks[0], rank=1)]], exclude={"c2"})
        self.assertNotIn("c2", out["context_ids"])


if __name__ == "__main__":
    unittest.main()
