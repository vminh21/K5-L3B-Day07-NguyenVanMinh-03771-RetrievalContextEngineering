"""Retrieval evaluation: Hit@1, Evidence Hit@3, Context Evidence Rate (+ MRR@10) on ONE split.

Usage:
  python -m src.eval_retrieval --method hybrid --split dev [--top-k 5] [--budget 3000]
         [--use-filter] [--neighbors] [--overflow skip|truncate] [--config NAME]

- The split is filtered BEFORE questions are used; only answerable questions (with `gold`) count.
- Hit definition (same as starter/baseline.py): chunk has the gold source_id and page and the
  evidence string is contained in its text. Any gold entry (alternatives) counts.
- Hit@1 / Hit@3 / MRR@10 come from one ranked list of the ORIGINAL question (no rewrite).
- Multi-hop questions (`gold_groups`): Hit@k = at least one required evidence in top-k;
  Context Evidence Rate requires EVERY group in the context.
- Context Evidence Rate: the evidence of a gold entry is inside the packed context (whitespace-
  normalised, to also cover truncated chunks) and a context chunk is on that gold page.
- --use-filter applies the question's `filter` field, which represents a filter supplied by the user
  together with the question (never derived from gold).
- Backend errors are recorded as status=error and counted as misses (kept in the denominator).
"""
import argparse
import json
import re
import statistics
import time
from pathlib import Path

from src.context import ContextPacker
from src.retrievers import RetrievalError, build

QUESTIONS = Path("data/day7/questions.json")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def is_hit(chunk: dict, gold: list[dict]) -> bool:
    return any(chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"] and g["evidence"] in chunk["text"]
               for g in gold)


_PAGE = {c["id"]: c["page"] for c in json.loads(Path("data/day7/chunks.json").read_text(encoding="utf-8"))}


def context_has_evidence(ctx: dict, hits: list[dict], gold: list[dict]) -> bool:
    # pages of EVERY chunk in the context (incl. neighbour chunks that are not in `hits`)
    pages = {_PAGE[i] for i in ctx["context_ids"]}
    text = norm(ctx["context_text"])
    return any(g["page"] in pages and norm(g["evidence"]) in text for g in gold)


def pct(n: int, d: int) -> dict:
    return {"n": n, "N": d, "pct": round(100 * n / d, 1) if d else None, "str": f"{n}/{d}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["dense", "bm25", "hybrid", "rerank"])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--top-k", type=int, default=5, help="chunks retrieved for the context")
    ap.add_argument("--budget", type=int, default=3000, help="context budget in characters")
    ap.add_argument("--use-filter", action="store_true")
    ap.add_argument("--neighbors", action="store_true")
    ap.add_argument("--overflow", default="skip", choices=["skip", "truncate"])
    ap.add_argument("--continuation-first", action="store_true")
    ap.add_argument("--dedup-text", action="store_true", help="hybrid only: merge identical-text chunks")
    ap.add_argument("--questions", type=Path, default=QUESTIONS)
    ap.add_argument("--config", help="results folder name (default derived from options)")
    a = ap.parse_args()

    questions = [q for q in json.loads(a.questions.read_text(encoding="utf-8")) if q["split"] == a.split]
    questions = [q for q in questions if q.get("gold")]  # answerable only
    name = a.config or f"{a.method}_k{a.top_k}_b{a.budget}" + ("_filter" if a.use_filter else "") + \
        ("_nb" if a.neighbors else "") + ("_trunc" if a.overflow == "truncate" else "") + ("_dd" if a.dedup_text else "") + ("_cf" if a.continuation_first else "")
    out_dir = Path("results/retrieval") / name / a.split

    t0 = time.perf_counter()
    retriever = build(a.method, **({"dedup_text": True} if a.dedup_text and a.method in ("hybrid", "rerank") else {}))
    init_s = time.perf_counter() - t0
    packer = ContextPacker(budget_chars=a.budget, neighbors=a.neighbors, overflow=a.overflow,
                           continuation_first=a.continuation_first)
    depth = max(10, a.top_k)  # rank list for Hit@1/3 and MRR@10

    traces, lat = [], []
    h1 = h3 = ctx_n = errors = 0
    rr = []
    for q in questions:
        flt = q.get("filter") if a.use_filter else None
        rec = {"query_id": q["id"], "type": q.get("type"), "query": q["question"], "query_mode": "original",
               "filter": flt}
        try:
            t = time.perf_counter()
            ranked = retriever.search(q["question"], filters=flt, top_k=depth)
            ms = (time.perf_counter() - t) * 1000
        except RetrievalError as e:
            errors += 1
            rec.update(status="error", error=str(e))
            traces.append(rec)
            rr.append(0.0)
            continue
        lat.append(ms)
        hits = [is_hit(c, q["gold"]) for c in ranked]
        first = next((i + 1 for i, h in enumerate(hits) if h), None)
        ctx = packer.pack([ranked[: a.top_k]])
        groups = q.get("gold_groups")  # multi-hop: every group must be in context
        c_ok = all(context_has_evidence(ctx, ranked[: a.top_k], g) for g in groups) if groups \
            else context_has_evidence(ctx, ranked[: a.top_k], q["gold"])
        h1 += bool(hits[:1] and hits[0]); h3 += any(hits[:3]); ctx_n += c_ok
        rr.append(1 / first if first else 0.0)
        rec.update(
            status="ok", latency_ms=round(ms, 1), first_hit_rank=first,
            hit1=bool(hits[:1] and hits[0]), hit3=any(hits[:3]), context_hit=c_ok,
            top3=[{"id": c["id"], "page": c["page"], "rank": c["rank"], "score": round(c["score"], 5),
                   "is_hit": hits[i], **({"component_ranks": c["component_ranks"]} if "component_ranks" in c else {})}
                  for i, c in enumerate(ranked[:3])],
            context_ids=ctx["context_ids"], context_chars=ctx["chars"], context_est_tokens=ctx["est_tokens"],
            n_candidates=ctx["n_candidates"], dropped_ids=ctx["dropped_ids"], truncated_ids=ctx["truncated_ids"],
            context_text=ctx["context_text"],
        )
        traces.append(rec)

    N = len(questions)
    summary = {
        "config": name, "split": a.split, "method": retriever.name, "retriever_params": retriever.params,
        "top_k_context": a.top_k, "context": packer.params, "filter": "question.filter (user-supplied)" if a.use_filter else None,
        "query_mode": "original question, no rewrite", "N_answerable": N,
        "hit@1": pct(h1, N), "evidence_hit@3": pct(h3, N), "context_evidence_rate": pct(ctx_n, N),
        "mrr@10": round(sum(rr) / N, 3) if N else None,
        "errors": errors,
        "median_latency_ms": round(statistics.median(lat), 1) if lat else None,
        "init_seconds": round(init_s, 2), "bm25_index_seconds": round(getattr(getattr(retriever, "lexical", retriever), "index_seconds", 0) or 0, 4),
        "cost_usd": 0.0, "cost_note": "local only: Ollama embeddinggemma + Postgres; no API calls",
        "questions_file": str(a.questions), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name:32s} {a.split}  Hit@1 {summary['hit@1']['str']:>6} ({summary['hit@1']['pct']}%)  "
          f"Hit@3 {summary['evidence_hit@3']['str']:>6} ({summary['evidence_hit@3']['pct']}%)  "
          f"CtxEv {summary['context_evidence_rate']['str']:>6} ({summary['context_evidence_rate']['pct']}%)  "
          f"MRR {summary['mrr@10']}  med {summary['median_latency_ms']} ms  errors {errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
