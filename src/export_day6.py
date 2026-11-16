"""Export one Day 6 strategy from pgvector to data/day7/chunks.json (Day 7 chunk schema).

Usage: python -m src.export_day6 [--strategy B] [--output data/day7/chunks.json]
The chunk IDs are kept exactly as stored in pgvector, so dense search (which reads
the database) and lexical methods (which read this file) use the same chunks.
"""
import argparse
import hashlib
import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from src import config

# Day 6 stored an absolute path on the author's machine; keep a portable path instead.
PORTABLE_SOURCE = "K5-L3B-Day06-NguyenVanMinh-2A202603771-DataIngestion/data/manifest.pdf"


def export(strategy: str) -> list[dict]:
    sql = """SELECT chunk_id, document_id, source, page, text, metadata
             FROM chunks WHERE strategy = %s ORDER BY page, chunk_id"""
    with psycopg.connect(config.DATABASE_URL, row_factory=dict_row) as conn:
        rows = conn.execute(sql, (strategy,)).fetchall()
    return [
        {
            "id": r["chunk_id"],
            "text": r["text"],
            "source_id": r["document_id"],
            "source": PORTABLE_SOURCE,
            "page": r["page"],
            "metadata": r["metadata"],
        }
        for r in rows
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=config.DAY6_STRATEGY)
    ap.add_argument("--output", type=Path, default=Path("data/day7/chunks.json"))
    args = ap.parse_args()

    chunks = export(args.strategy)
    ids = [c["id"] for c in chunks]
    assert chunks, f"no chunks for strategy {args.strategy}"
    assert len(ids) == len(set(ids)), "duplicate chunk IDs"
    fields = {"id", "text", "source_id", "source", "page", "metadata"}
    assert all(set(c) == fields and c["text"].strip() for c in chunks), "bad chunk record"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(chunks, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(data, encoding="utf-8")
    pages = sorted({c["page"] for c in chunks})
    print(f"strategy={args.strategy} chunks={len(chunks)} pages={pages[0]}-{pages[-1]} ({len(pages)} pages)")
    print(f"wrote {args.output}  sha256={hashlib.sha256(data.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
