"""Context packing: merge retrieval results -> deduplicated, source-labelled context within a budget.

Budget unit: CHARACTERS of the final context text, headers included (tokens ≈ chars / 4, reported too).
Strategy B chunks are ≤ 1000 chars (mean ≈ 690), so the starter's 800-char budget would often fit
only one chunk; default here is 3000.

Fix for the starter's known issue (first search fills the budget, later searches add nothing):
candidates from several searches are interleaved by rank (all rank-1 hits first, then rank-2, ...),
not appended search by search.
"""
from src.retrievers.base import load_chunks


def header(c: dict) -> str:
    chapter = (c.get("metadata") or {}).get("chapter", "?")
    return f"[{c['id']} | {c['source_id']} | page {c['page']} | {chapter}]"


def block(c: dict, text: str | None = None) -> str:
    return f"{header(c)}\n{(text if text is not None else c['text']).strip()}"


def _truncate_sentences(text: str, max_chars: int) -> str | None:
    """Keep whole leading sentences that fit; None if not even one fits."""
    out = ""
    for part in text.replace("\n", " ").split(". "):
        cand = (out + ". " if out else "") + part.strip()
        if len(cand) + 2 > max_chars:
            break
        out = cand
    return out + ". […]" if out else None


class ContextPacker:
    def __init__(self, budget_chars: int = 3000, neighbors: bool = False, overflow: str = "skip",
                 chunks: list[dict] | None = None):
        if overflow not in ("skip", "truncate"):
            raise ValueError("overflow must be 'skip' or 'truncate'")
        self.budget, self.neighbors, self.overflow = budget_chars, neighbors, overflow
        self.params = {"budget_chars": budget_chars, "neighbors": neighbors, "overflow": overflow,
                       "order": "interleave by rank across searches", "dedup": "chunk id"}
        if neighbors:
            all_chunks = chunks if chunks is not None else load_chunks()
            # chunks.json is ordered by (page, chunk_id) = reading order
            self.prev = {b["id"]: a for a, b in zip(all_chunks, all_chunks[1:])}
            self.next = {a["id"]: b for a, b in zip(all_chunks, all_chunks[1:])}

    def pack(self, result_lists: list[list[dict]]) -> dict:
        """result_lists: one ranked list per search call. Returns context + trace info."""
        n_candidates = sum(len(r) for r in result_lists)
        # interleave: (rank, search order) — every search's best hit before any second-best hit
        ordered = sorted(
            ((h.get("rank", i + 1), s, h) for s, hits in enumerate(result_lists) for i, h in enumerate(hits)),
            key=lambda t: (t[0], t[1]),
        )
        seen, picked = set(), []
        for _, _, h in ordered:
            if h["id"] in seen:
                continue
            seen.add(h["id"])
            picked.append(h)
            if self.neighbors:  # add adjacent chunks right after the hit (passage continuity)
                for nb in (self.prev.get(h["id"]), self.next.get(h["id"])):
                    if nb and nb["id"] not in seen and nb["page"] in (h["page"] - 1, h["page"], h["page"] + 1):
                        seen.add(nb["id"])
                        picked.append({**nb, "neighbor_of": h["id"]})

        blocks, ids, used, dropped, truncated = [], [], 0, [], []
        for c in picked:
            b = block(c)
            sep = 2 if blocks else 0  # "\n\n" between blocks
            if used + sep + len(b) <= self.budget:
                blocks.append(b); ids.append(c["id"]); used += sep + len(b)
                continue
            if self.overflow == "truncate":
                room = self.budget - used - sep - len(header(c)) - 1
                t = _truncate_sentences(c["text"], room) if room > 80 else None
                if t:
                    b = block(c, t)
                    blocks.append(b); ids.append(c["id"]); used += sep + len(b); truncated.append(c["id"])
                    continue
            dropped.append(c["id"])

        text = "\n\n".join(blocks)
        return {
            "context_text": text,
            "context_ids": ids,
            "chars": len(text),
            "est_tokens": round(len(text) / 4),
            "n_candidates": n_candidates,
            "n_unique": len(picked),
            "dropped_ids": dropped,
            "truncated_ids": truncated,
            "neighbor_ids": [c["id"] for c in picked if "neighbor_of" in c and c["id"] in ids],
        }
