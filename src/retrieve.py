"""CLI: python -m src.retrieve --method {dense,bm25,hybrid} [--top-k 5] [--chapter "Chapter I"] "query" """
import argparse
import time

from src.retrievers import RetrievalError, build


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--method", default="hybrid", choices=["dense", "bm25", "hybrid", "rerank"])
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--chapter", help="metadata filter supplied by the user, e.g. 'Chapter II'")
    a = ap.parse_args()
    try:
        r = build(a.method)
        t0 = time.perf_counter()
        hits = r.search(a.query, filters={"chapter": a.chapter} if a.chapter else None, top_k=a.top_k)
    except RetrievalError as e:
        print(f"status=error: {e}")
        return 2
    print(f"method={r.name} params={r.params} ({(time.perf_counter() - t0) * 1000:.0f} ms)")
    for h in hits:
        extra = f" ranks={h['component_ranks']}" if "component_ranks" in h else ""
        print(f"{h['rank']}. {h['id']} p{h['page']} {h['metadata'].get('chapter')} score={h['score']:.4f}{extra}")
        print("   " + " ".join(h["text"].split())[:110])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
