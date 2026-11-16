"""Run the agent on one split. The agent only ever receives id, question and the user filter.

  python -m src.run_agent --split dev --method hybrid [--ids q01,qn01] [--config NAME]
         [--top-k 5] [--max-searches 3] [--budget 6000] [--no-filter]

Writes results/agent/<config>/<split>/{traces.json, summary.json}. Re-running with --ids merges
into existing traces (same query_id is replaced).
"""
import argparse
import json
import statistics
import time
from pathlib import Path

from src import config
from src.agent import Agent
from src.llm import LLM, CostLedger
from src.retrievers import RetrievalError, build

CASES = Path("data/day7/cases.json")


def load_inputs(split: str) -> list[dict]:
    """Strip everything except what a real user would send: id, question, filter."""
    rows = [c for c in json.loads(CASES.read_text(encoding="utf-8")) if c["split"] == split]
    return [{"id": c["id"], "question": c["question"], "filter": c.get("filter")} for c in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--method", default="hybrid", choices=["dense", "bm25", "hybrid"])
    ap.add_argument("--ids", help="comma-separated subset of case ids")
    ap.add_argument("--config")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--max-searches", type=int, default=3)
    ap.add_argument("--budget", type=int, default=6000)
    ap.add_argument("--per-search-budget", type=int, default=3000)
    ap.add_argument("--neighbors", action="store_true")
    ap.add_argument("--prompt", default="v1", choices=["v1", "v2"])
    ap.add_argument("--no-filter", action="store_true", help="ignore the user-supplied filter")
    a = ap.parse_args()

    cases = load_inputs(a.split)
    if a.ids:
        want = set(a.ids.split(","))
        cases = [c for c in cases if c["id"] in want]
    name = a.config or f"agent_{a.method}_k{a.top_k}_s{a.max_searches}"
    out_dir = Path("results/agent") / name / a.split
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger = CostLedger()
    print(f"spent so far ${ledger.spent():.4f} / cap ${ledger.cap:.2f}")
    try:
        retriever = build(a.method)
        agent = Agent(retriever, LLM(ledger=ledger), top_k=a.top_k, max_searches=a.max_searches,
                      budget_chars=a.budget, per_search_budget=a.per_search_budget, neighbors=a.neighbors,
                      prompt=a.prompt)
    except RetrievalError as e:
        agent, init_error = None, str(e)

    traces_path = out_dir / "traces.json"
    traces = {t["query_id"]: t for t in json.loads(traces_path.read_text())} if traces_path.exists() else {}
    for c in cases:
        flt = None if a.no_filter else c["filter"]
        if agent is None:
            r = {"status": "error", "error": f"init: {init_error}", "events": [], "citations": []}
        else:
            r = agent.run(c["question"], filters=flt)
        traces[c["id"]] = {"query_id": c["id"], "config": name, "model": config.LLM_MODEL,
                           "question": c["question"], "filter": flt, **r}
        cost = r.get("cost_usd", 0)
        print(f"{c['id']:5s} {r['status']:8s} searches={sum(e['event']=='search' for e in r['events'])} "
              f"cites={len(r['citations'])} ${cost:.5f} {r.get('elapsed_ms', 0)}ms "
              f"{(r.get('answer') or r.get('error') or '')[:90]}")
        traces_path.write_text(json.dumps(list(traces.values()), ensure_ascii=False, indent=2) + "\n")

    tr = list(traces.values())
    ok = [t for t in tr if t["status"] != "error"]
    summary = {
        "config": name, "split": a.split, "agent": agent.params if agent else None, "n_cases": len(tr),
        "status": {s: sum(t["status"] == s for t in tr) for s in ("answered", "abstain", "error")},
        "tool_use": f"{sum(any(e['event']=='search' for e in t['events']) for t in ok)}/{len(ok)}",
        "avg_searches": round(statistics.mean(sum(e['event'] == 'search' for e in t['events']) for t in ok), 2) if ok else None,
        "tokens_in": sum(t.get("tokens_in", 0) for t in tr), "tokens_out": sum(t.get("tokens_out", 0) for t in tr),
        "cost_usd": round(sum(t.get("cost_usd", 0) for t in tr), 5),
        "median_latency_ms": statistics.median(t["elapsed_ms"] for t in ok) if ok else None,
        "errors": [{"query_id": t["query_id"], "error": t["error"]} for t in tr if t["status"] == "error"],
        "note": "answer quality / citation support / abstention correctness are labelled manually in reviews.json",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"run cost ${summary['cost_usd']:.4f}; total spent ${ledger.spent():.4f} / cap ${ledger.cap:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
