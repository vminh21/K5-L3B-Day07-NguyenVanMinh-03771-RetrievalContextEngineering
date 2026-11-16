"""Re-score stored retrieval traces against the CURRENT gold (used after the round-3 gold completion).
Nothing is re-run: Hit@1/Hit@3 use the stored top-3, Context Evidence Rate the stored context text.
MRR@10 cannot be recomputed (only top-3 stored) and is omitted.
  python -m src.rescore_retrieval results/retrieval/<config>/<split> data/day7/<questions>.json
"""
import json
import sys
from pathlib import Path

from src.eval_retrieval import norm

chunks = {c["id"]: c for c in json.loads(Path("data/day7/chunks.json").read_text())}


def hit(cid, gold):
    c = chunks[cid]
    return any(c["source_id"] == g["source_id"] and c["page"] == g["page"] and g["evidence"] in c["text"] for g in gold)


def ctx_ok(rec, gold):
    pages = {chunks[i]["page"] for i in rec["context_ids"]}
    text = norm(rec["context_text"])
    return any(g["page"] in pages and norm(g["evidence"]) in text for g in gold)


def rescore(trace_dir, qfile):
    Q = {q["id"]: q for q in json.loads(Path(qfile).read_text())}
    T = json.loads((Path(trace_dir) / "traces.json").read_text())
    n = len(T)
    h1 = sum(hit(r["top3"][0]["id"], Q[r["query_id"]]["gold"]) for r in T if r["top3"])
    h3 = sum(any(hit(x["id"], Q[r["query_id"]]["gold"]) for x in r["top3"]) for r in T)
    cx = sum(ctx_ok(r, Q[r["query_id"]]["gold"]) for r in T)
    old = json.loads((Path(trace_dir) / "summary.json").read_text())
    return {"N": n, "hit@1": (old["hit@1"]["str"], f"{h1}/{n}"), "hit@3": (old["evidence_hit@3"]["str"], f"{h3}/{n}"),
            "ctx": (old["context_evidence_rate"]["str"], f"{cx}/{n}")}


if __name__ == "__main__":
    print(json.dumps(rescore(sys.argv[1], sys.argv[2])))
