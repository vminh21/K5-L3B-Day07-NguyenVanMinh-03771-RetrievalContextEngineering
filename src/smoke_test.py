"""Checkpoint 1 smoke test: embed a question -> dense search on Day 6 pgvector."""
import sys
import time

from src import config
from src.embeddings import MyEmbedder
from src.store import PgVectorStore


def main() -> int:
    question = sys.argv[1] if len(sys.argv) > 1 else "What is the history of all hitherto existing society?"
    emb = MyEmbedder(model_name=config.EMBEDDING_MODEL, base_url=config.OLLAMA_BASE_URL)
    store = PgVectorStore(config.DATABASE_URL, dimensions=emb.dimensions)
    print(f"embedding={emb.model_name} dims={emb.dimensions} strategy={config.DAY6_STRATEGY}")
    t0 = time.perf_counter()
    hits = store.search(config.DAY6_STRATEGY, emb.embed_query(question), top_k=3)
    print(f"query: {question!r}  ({(time.perf_counter() - t0) * 1000:.0f} ms)")
    for i, h in enumerate(hits, 1):
        print(f"{i}. {h['chunk_id']}  page={h['page']}  score={h['score']:.4f}  source={h['source']}")
        print("   " + h["text"][:120].replace("\n", " "))
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
