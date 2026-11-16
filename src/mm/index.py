"""Build the multimodal index for the NASA FY 2024 AFR from data/advanced/extract/p*.json.

Chunks (data/advanced/index/mm_chunks.json, same fields as Day 7 chunks so all retrievers/agent work):
  * text   : text layer of each page, split on blank lines / sentences into <= 1000 chars
  * visual : one chunk per table/chart/diagram/map/infographic/photo transcribed by the vision model,
             text = "[KIND] title\\n content"; long tables are split into parts that repeat the title + header.
             metadata keeps page, kind, bbox (0-1000) and the crop path for checking against the original.
Every chunk keeps page (PDF) and printed_page; metadata.chapter = section name from the PDF outline.

Vectors: embeddinggemma (768-d, Ollama) into the Day 6 pgvector table `chunks` with strategy = "MM"
(a separate partition; Day 6 strategies A/B/C untouched).

    python -m src.mm.index [--no-embed]
"""
import argparse
import json
import re
from pathlib import Path

PDF = Path("data/advanced/raw/nasa_afr_fy2024.pdf")
EXTRACT = Path("data/advanced/extract")
OUT = Path("data/advanced/index/mm_chunks.json")
SOURCE_ID = "nasa-afr-fy2024"
SOURCE = "NASA FY 2024 Agency Financial Report (nasa-fy-2024-afr.pdf)"
STRATEGY = "MM"
DOC_TITLE = "NASA FY 2024 Agency Financial Report"
MAX = 1000


def sections(doc) -> dict[int, str]:
    """page -> deepest outline title (level <= 2) starting at or before that page."""
    toc = [(p, t.strip()) for lvl, t, p in doc.get_toc() if lvl <= 2]
    out, cur = {}, "Front matter"
    for n in range(1, doc.page_count + 1):
        for p, t in toc:
            if p == n:
                cur = re.sub(r"\s+", " ", t)
        out[n] = cur
    return out


def split_text(text: str, limit: int = MAX) -> list[str]:
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s*\n", text)]
    paras = [p for p in paras if len(p) > 2]
    chunks, cur = [], ""
    for p in paras:
        while len(p) > limit:  # very long paragraph: cut at sentence boundary
            cut = p.rfind(". ", 0, limit)
            cut = cut + 1 if cut > limit // 2 else limit
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(p[:cut].strip())
            p = p[cut:].strip()
        if cur and len(cur) + 1 + len(p) > limit:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        chunks.append(cur)
    return [c for c in chunks if len(c) >= 40]


def split_visual(head: str, content: str, limit: int = 1800) -> list[str]:
    if len(head) + len(content) <= limit:
        return [f"{head}\n{content}"]
    lines = content.splitlines()
    table_head = [l for l in lines[:2] if l.startswith("|")]
    body = lines[len(table_head):]
    parts, cur = [], []
    for l in body:
        if cur and len(head) + sum(len(x) + 1 for x in table_head + cur + [l]) > limit:
            parts.append(cur)
            cur = []
        cur.append(l)
    if cur:
        parts.append(cur)
    return [f"{head} (part {i}/{len(parts)})\n" + "\n".join(table_head + p) for i, p in enumerate(parts, 1)]


def build() -> list[dict]:
    import pymupdf
    doc = pymupdf.open(PDF)
    sec = sections(doc)
    chunks = []
    for f in sorted(EXTRACT.glob("p*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        n = j["page"]
        base = {"source_id": SOURCE_ID, "source": SOURCE, "page": n}
        for i, t in enumerate(split_text(j["text_layer"])):
            chunks.append({**base, "id": f"nasa_p{n:03d}_t{i}", "text": t,
                           "metadata": {"chapter": sec[n], "kind": "text", "printed_page": n - 1}})
        for i, e in enumerate(j["elements"]):
            kind = (e.get("kind") or "visual").lower()
            head = f"[{kind.upper()}] {e.get('title', '').strip()} (page {n})"
            for k, part in enumerate(split_visual(head, (e.get("content") or "").strip())):
                chunks.append({**base, "id": f"nasa_p{n:03d}_v{i}" + (f"_{k}" if k else ""), "text": part,
                               "metadata": {"chapter": sec[n], "kind": kind, "printed_page": n - 1,
                                            "title": e.get("title"), "bbox": e.get("bbox"), "crop": e.get("crop")}})
    return chunks


def embed_and_store(chunks: list[dict]):
    from src import config
    from src.embeddings import MyEmbedder
    from src.models import Chunk
    from src.store import PgVectorStore
    emb = MyEmbedder(model_name=config.EMBEDDING_MODEL, base_url=config.OLLAMA_BASE_URL, doc_title=DOC_TITLE)
    store = PgVectorStore(config.DATABASE_URL, dimensions=emb.dimensions)
    vecs = emb.embed_documents([c["text"] for c in chunks])
    import psycopg
    with psycopg.connect(config.DATABASE_URL) as conn:  # rebuild the MM partition only
        conn.execute("DELETE FROM chunks WHERE strategy = %s", (STRATEGY,))
    store.upsert(STRATEGY, [Chunk(c["id"], c["source_id"], c["source"], c["page"], c["text"], c["metadata"])
                            for c in chunks], vecs)
    print(f"embedded {len(vecs)} chunks ({emb.dimensions}-d) into pgvector strategy={STRATEGY}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-embed", action="store_true")
    a = ap.parse_args()
    chunks = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(chunks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds = {}
    for c in chunks:
        kinds[c["metadata"]["kind"]] = kinds.get(c["metadata"]["kind"], 0) + 1
    print(f"{len(chunks)} chunks from {len(list(EXTRACT.glob('p*.json')))} pages: {kinds}")
    if not a.no_embed:
        embed_and_store(chunks)
