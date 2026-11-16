"""Run the multimodal agent on the advanced benchmark. The agent receives ONLY id + question.

    python -m src.mm.run --split dev --config mm_rerank_k5_view [--method rerank] [--top-k 5]
                         [--no-view] [--no-kind] [--ids D-TB1,D-NE1]

Writes results/advanced/<config>/<split>/{traces.json, summary.json}. `auto_check` is only an aid for
reading dev results (numbers of the expected answer found in the answer + cited page overlaps an evidence
page); test labels are assigned by hand in results/advanced/<config>/test/labels.json.
"""
import argparse
import json
import re
import statistics
from pathlib import Path

from src.llm import LLM, CostLedger
from src.mm.agent import MMAgent, build_retriever

BENCH = Path("data/advanced/benchmark")
OUT = Path("results/advanced")


def nums(s: str) -> set[str]:
    return {x.replace(",", "") for x in re.findall(r"\d[\d,]*\.?\d*", s or "") if len(x.replace(",", "")) >= 2}


def auto_check(case: dict, tr: dict) -> dict:
    if case["group"] == "no_evidence":
        return {"auto_pass": tr["status"] == "abstain", "why": tr["status"]}
    if tr["status"] != "answered":
        return {"auto_pass": False, "why": tr["status"]}
    missing = sorted(nums(case["expected_answer"]) - nums(tr["answer"]))
    ev_pages = {e["page"] for e in case["evidence"]}
    page_ok = bool(ev_pages & set(tr["cited_pages"]))
    return {"auto_pass": not missing and page_ok, "missing_numbers": missing, "cited_pages": tr["cited_pages"],
            "evidence_pages": sorted(ev_pages)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--method", default="rerank", choices=["dense", "bm25", "hybrid", "rerank"])
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--max-steps", type=int, default=5)
    ap.add_argument("--budget", type=int, default=12000)
    ap.add_argument("--no-view", action="store_true")
    ap.add_argument("--no-kind", action="store_true")
    ap.add_argument("--ids")
    a = ap.parse_args()

    cases = json.loads((BENCH / f"{a.split}.json").read_text(encoding="utf-8"))
    if a.ids:
        cases = [c for c in cases if c["id"] in set(a.ids.split(","))]
    out = OUT / a.config / a.split
    out.mkdir(parents=True, exist_ok=True)
    ledger = CostLedger()
    print(f"spent so far ${ledger.spent():.4f} / cap ${ledger.cap:.2f}")
    agent = MMAgent(build_retriever(a.method), LLM(ledger=ledger), top_k=a.top_k, max_steps=a.max_steps,
                    budget_chars=a.budget, view_page=not a.no_view, kind_filter=not a.no_kind)
    tpath = out / "traces.json"
    traces = {t["id"]: t for t in json.loads(tpath.read_text())} if tpath.exists() and a.ids else {}
    for c in cases:
        tr = agent.run(c["question"])          # <- only the question goes in
        rec = {"id": c["id"], "group": c["group"], "question": c["question"], **tr}
        rec["auto_check"] = auto_check(c, tr)
        traces[c["id"]] = rec
        print(f"{c['id']:7s} {tr['status']:8s} {'PASS' if rec['auto_check']['auto_pass'] else 'fail'} "
              f"${tr['cost_usd']:.4f} {tr['elapsed_ms'] / 1000:5.1f}s pages={tr['cited_pages']} "
              f"views={tr['n_views']} | {(tr['answer'] or tr['error'] or '')[:150]}", flush=True)
    rows = [traces[k] for k in sorted(traces)]
    tpath.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    groups = sorted({r["group"] for r in rows})
    summ = {"config": a.config, "split": a.split, "agent_params": agent.params, "n": len(rows),
            "auto_pass": sum(r["auto_check"]["auto_pass"] for r in rows),
            "by_group": {g: f"{sum(r['auto_check']['auto_pass'] for r in rows if r['group'] == g)}/"
                            f"{sum(r['group'] == g for r in rows)}" for g in groups},
            "errors": sum(r["status"] == "error" for r in rows),
            "cost_usd": round(sum(r["cost_usd"] for r in rows), 5),
            "median_s": round(statistics.median(r["elapsed_ms"] for r in rows) / 1000, 1),
            "p95_s": round(sorted(r["elapsed_ms"] for r in rows)[int(0.95 * (len(rows) - 1))] / 1000, 1)}
    (out / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "agent_params"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
