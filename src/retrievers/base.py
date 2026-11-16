"""Shared helpers: result format, filter matching, explicit error type."""
import json
from pathlib import Path

CHUNKS_PATH = Path(__file__).resolve().parents[2] / "data/day7/chunks.json"
FIELDS = ("id", "text", "source_id", "source", "page", "metadata")


class RetrievalError(RuntimeError):
    """Raised when a backend (Postgres, Ollama) fails. Callers record status='error';
    retrievers never silently fall back to another method."""


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def matches(chunk: dict, filters: dict | None) -> bool:
    """Same semantics as the Day 6 SQL filter: metadata->>key = str(value); None values ignored."""
    if not filters:
        return True
    md = chunk.get("metadata") or {}
    return all(str(md.get(k)) == str(v) for k, v in filters.items() if v is not None)


def result(chunk: dict, score: float, rank: int, strategy: str, **extra) -> dict:
    out = {k: chunk[k] for k in FIELDS}
    out.update(score=float(score), rank=rank, strategy=strategy, **extra)
    return out
