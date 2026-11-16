"""Retrieval-only comparison on the advanced benchmark (no LLM cost): page hit@k / MRR of evidence pages
for dense, BM25, hybrid RRF and hybrid+rerank over the MM index, using the raw question as query.

    python -m src.mm.eval_retrieval --split dev
"""
import argparse
import json
from pathlib import Path

from src.mm.agent import build_retriever

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="dev")
a = ap.parse_args()
cases = [c for c in json.loads(Path(f"data/advanced/benchmark/{a.split}.json").read_text()) if c["group"] != "no_evidence"]
rows = {}
for m in ["dense", "bm25", "hybrid", "rerank"]:
    r = build_retriever(m)
    h1 = h3 = h5 = h10 = mrr = 0
    per = {}
    for c in cases:
        ev = {e["page"] for e in c["evidence"]}
        pages = [x["page"] for x in r.search(c["question"], top_k=10)]
        rank = next((i for i, p in enumerate(pages, 1) if p in ev), None)
        per[c["id"]] = rank
        h1 += bool(rank and rank <= 1); h3 += bool(rank and rank <= 3); h5 += bool(rank and rank <= 5)
        h10 += bool(rank); mrr += 1 / rank if rank else 0
    n = len(cases)
    rows[m] = {"hit@1": round(h1 / n, 3), "hit@3": round(h3 / n, 3), "hit@5": round(h5 / n, 3),
               "hit@10": round(h10 / n, 3), "MRR@10": round(mrr / n, 3), "first_evidence_rank": per}
    print(f"{m:7s} n={n} " + " ".join(f"{k}={v}" for k, v in rows[m].items() if k != "first_evidence_rank"), flush=True)
out = Path(f"results/advanced/retrieval_{a.split}.json")
out.write_text(json.dumps(rows, indent=1) + "\n")
miss = {m: [k for k, v in rows[m]["first_evidence_rank"].items() if not v or v > 5] for m in rows}
print("misses@5:", miss)
