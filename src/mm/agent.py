"""Multimodal agent for the NASA FY 2024 AFR (advanced challenge).

Tools (Responses API function calling, strict schemas):
  search(query, kind)      hybrid (dense pgvector + BM25, RRF) [+ cross-encoder rerank] over text chunks AND
                           visual-element transcriptions; `kind` restricts to text/table/chart/diagram/map/...
  view_page(page, focus)   sends the ORIGINAL page image (150 dpi render) to the vision model with a focused
                           question; only pages already returned by search may be viewed (keeps it grounded).
  final_answer(answer, citations, abstain)
Citations: [S#] = retrieved chunk, [V#] = page view. Every cited label maps to a PDF page.
Gold answers / evidence never enter this module: it only receives the question.
"""
import base64
import json
import re
import time
from pathlib import Path

from src import config
from src.agent import SYSTEM_MM
from src.llm import LLM, BudgetExceeded, cost_of
from src.retrievers import RetrievalError

PAGES = Path("data/advanced/pages")
PDF = Path("data/advanced/raw/nasa_afr_fy2024.pdf")
ABSTAIN_TEXT = "Not enough evidence in the document to answer this question."
KINDS = ["any", "text", "table", "chart", "diagram", "map", "infographic", "photo"]

VIEW_RULES = """
9. `view_page` shows you the original page image of a page that search already returned. Use it when a \
passage from a chart, diagram, map or table is unclear, incomplete, or you must check a colour/legend/year, \
or when the question is about something visual that the transcription may not capture. Cite page views as [V#].
10. Cite every label that supports a part of your answer; for multi-part questions cite the passage(s) for each part."""

TOOLS_BASE = [
    {"type": "function", "name": "search", "strict": True,
     "description": "Search the report. Returns labelled passages (prose text, or transcriptions of tables, "
                    "charts, diagrams, maps, infographics, photos) with page numbers.",
     "parameters": {"type": "object", "additionalProperties": False, "required": ["query", "kind"],
                    "properties": {
                        "query": {"type": "string", "description": "search query in English"},
                        "kind": {"type": "string", "enum": KINDS,
                                 "description": "restrict to one content type, or 'any'"}}}},
    {"type": "function", "name": "final_answer", "strict": True,
     "description": "Finish. Give the grounded answer with citations, or abstain if evidence is insufficient.",
     "parameters": {"type": "object", "additionalProperties": False, "required": ["answer", "citations", "abstain"],
                    "properties": {
                        "answer": {"type": "string", "description": "answer with [S#]/[V#] citations; empty if abstaining"},
                        "citations": {"type": "array", "items": {"type": "string"}, "description": "labels like S1, V1"},
                        "abstain": {"type": "boolean"}}}},
]
VIEW_TOOL = {"type": "function", "name": "view_page", "strict": True,
             "description": "Look at the original page image (only pages returned by search) and read what is "
                            "needed for the question: values, legend colours, labels, connections.",
             "parameters": {"type": "object", "additionalProperties": False, "required": ["page", "focus"],
                            "properties": {
                                "page": {"type": "integer", "description": "PDF page number shown in a passage"},
                                "focus": {"type": "string", "description": "what to read on the page"}}}}

VIEW_PROMPT = """You are looking at page {page} of NASA's FY 2024 Agency Financial Report.
Read exactly what is printed on this page that is relevant to: {focus}
Report values with their labels, legend colours, years and units exactly as printed. For diagrams/maps, give
labels and the relationships shown (lines, arrows, levels, 'managed by'). If the page does not show it, say
"NOT ON THIS PAGE". Do not use outside knowledge. Plain text, at most 200 words."""


def page_png(n: int) -> Path:
    p = PAGES / f"p{n:03d}.png"
    if not p.exists():
        import pymupdf
        PAGES.mkdir(parents=True, exist_ok=True)
        pymupdf.open(PDF)[n - 1].get_pixmap(dpi=150).save(p)
    return p


class MMAgent:
    def __init__(self, retriever, llm: LLM | None = None, *, top_k: int = 5, max_steps: int = 5,
                 budget_chars: int = 12000, view_page: bool = True, kind_filter: bool = True):
        self.retriever, self.llm = retriever, llm or LLM()
        self.top_k, self.max_steps, self.budget = top_k, max_steps, budget_chars
        self.view, self.kind_filter = view_page, kind_filter
        self.system = SYSTEM_MM + (VIEW_RULES if view_page else "")
        tools = [dict(t) for t in TOOLS_BASE]
        if not kind_filter:  # ablation: plain search(query)
            tools[0] = {**tools[0], "parameters": {**tools[0]["parameters"], "required": ["query"],
                                                   "properties": {"query": tools[0]["parameters"]["properties"]["query"]}}}
        self.tools = tools + ([VIEW_TOOL] if view_page else [])
        self.params = {"retriever": retriever.name, "retriever_params": retriever.params, "top_k": top_k,
                       "max_steps": max_steps, "budget_chars": budget_chars, "view_page": view_page,
                       "kind_filter": kind_filter, "llm": self.llm.params}

    def _view(self, page: int, focus: str) -> tuple[str, dict]:
        self.llm.ledger.check()
        img = "data:image/png;base64," + base64.b64encode(page_png(page).read_bytes()).decode()
        t0 = time.perf_counter()
        r = self.llm.client.responses.create(
            model=self.llm.model, reasoning={"effort": "low"}, max_output_tokens=2500, store=False,
            input=[{"role": "user", "content": [{"type": "input_text", "text": VIEW_PROMPT.format(page=page, focus=focus)},
                                                {"type": "input_image", "image_url": img}]}])
        u = r.usage
        c = cost_of(u.input_tokens, u.output_tokens)
        self.llm.ledger.add(tag="mm_view_page", model=self.llm.model, tokens_in=u.input_tokens,
                            tokens_out=u.output_tokens, cost_usd=c,
                            reasoning_tokens=getattr(u.output_tokens_details, "reasoning_tokens", 0))
        return r.output_text.strip(), {"tokens_in": u.input_tokens, "tokens_out": u.output_tokens, "cost_usd": c,
                                       "ms": (time.perf_counter() - t0) * 1000}

    def run(self, question: str) -> dict:
        t0 = time.perf_counter()
        labels: dict[str, dict] = {}   # S#/V# -> {"id"/"page", ...}
        seen_ids, seen_pages, used = set(), set(), 0
        events, usage = [], {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "n_llm_calls": 0, "n_views": 0}
        inp: list = [{"role": "user", "content": f"Question: {question}"}]
        context: list[str] = []

        def acc(u):
            for k in ("tokens_in", "tokens_out", "cost_usd"):
                usage[k] += u[k]

        def finish(status, answer, cits, error=None, extra=None):
            return {"status": status, "answer": answer, "citations": cits,
                    "cited_pages": sorted({c["page"] for c in cits}), "events": events,
                    "context": "\n\n".join(context), "error": error,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000), **usage, **(extra or {})}

        try:
            n_tool = 0
            for _ in range(self.max_steps + 3):
                resp, u = self.llm.call(instructions=self.system, input=inp, tools=self.tools, tag="mm_agent")
                usage["n_llm_calls"] += 1
                acc(u)
                inp += resp.output
                calls = [o for o in resp.output if o.type == "function_call"]
                if not calls:
                    return finish("abstain", ABSTAIN_TEXT, [], extra={"stop": "no_tool_call"})
                call = calls[0]
                args = json.loads(call.arguments)

                if call.name == "final_answer":
                    events.append({"event": "answer", "raw": args})
                    if args["abstain"]:
                        return finish("abstain", ABSTAIN_TEXT, [], extra={"stop": "model_abstained",
                                                                         "model_answer": args["answer"]})
                    cited = [c.strip("[] ") for c in args["citations"]]
                    in_text = set(re.findall(r"\[([SV]\d+)\]", args["answer"]))
                    ok = bool(cited) and all(c in labels for c in cited) and in_text and in_text <= set(labels)
                    if not ok:
                        events.append({"event": "invalid_or_missing_citations", "citations": cited})
                        return finish("abstain", ABSTAIN_TEXT, [], extra={"stop": "invalid_citations",
                                                                         "model_answer": args["answer"]})
                    labs = list(dict.fromkeys(cited + sorted(in_text)))
                    cits = [{"label": l, **labels[l]} for l in labs]

                    def sub(m):
                        x = labels[m.group(1)]
                        return f"[{x['id']}]" if "id" in x else f"[page {x['page']} image]"
                    answer = re.sub(r"\[([SV]\d+)\]", sub, args["answer"])
                    return finish("answered", answer, cits, extra={"stop": "final_answer"})

                if n_tool >= self.max_steps:
                    out = "Tool limit reached. Call final_answer now (abstain if the evidence is insufficient)."
                    events.append({"event": "step_limit"})
                elif call.name == "view_page":
                    n_tool += 1
                    page = int(args["page"])
                    if page not in seen_pages:
                        out = f"Page {page} was not returned by search; search first."
                        events.append({"event": "view_page_refused", "page": page})
                    else:
                        text, vu = self._view(page, args["focus"])
                        acc(vu)
                        usage["n_views"] += 1
                        lab = f"V{sum(l.startswith('V') for l in labels) + 1}"
                        labels[lab] = {"page": page, "kind": "page_image"}
                        out = f"[{lab}] (page {page}, original page image)\n{text}"
                        context.append(f"[page {page} image | focus: {args['focus']}]\n{text}")
                        events.append({"event": "view_page", "tool": "view_page", "page": page, "focus": args["focus"],
                                       "label": lab, "observation": text, "elapsed_ms": round(vu["ms"])})
                else:  # search
                    n_tool += 1
                    ts = time.perf_counter()
                    kind = args.get("kind", "any")
                    filters = {"kind": kind} if kind and kind != "any" else None
                    results = self.retriever.search(args["query"], filters=filters, top_k=self.top_k)
                    lines, added = [], []
                    for r in results:
                        seen_pages.add(r["page"])
                        if r["id"] in seen_ids:
                            continue
                        txt = r["text"].strip()
                        if used + len(txt) > self.budget:
                            continue
                        used += len(txt)
                        seen_ids.add(r["id"])
                        lab = f"S{sum(l.startswith('S') for l in labels) + 1}"
                        md = r.get("metadata") or {}
                        labels[lab] = {"id": r["id"], "page": r["page"], "kind": md.get("kind")}
                        added.append(r["id"])
                        context.append(f"[{r['id']} | page {r['page']} | {md.get('kind')}]\n{txt}")
                        lines.append(f"[{lab}] (page {r['page']}, {md.get('kind')}, {md.get('chapter', '?')})\n{txt}")
                    out = "\n\n".join(lines) if lines else "No new passages found (already shown or nothing relevant)."
                    events.append({"event": "search", "tool": self.retriever.name, "query": args["query"], "kind": kind,
                                   "results": [{"id": r["id"], "page": r["page"], "rank": r["rank"],
                                                "kind": (r.get("metadata") or {}).get("kind"),
                                                "score": round(r["score"], 5)} for r in results],
                                   "added_ids": added, "elapsed_ms": round((time.perf_counter() - ts) * 1000)})
                inp.append({"type": "function_call_output", "call_id": call.call_id, "output": out})
            return finish("abstain", ABSTAIN_TEXT, [], extra={"stop": "turn_limit"})
        except (RetrievalError, BudgetExceeded) as e:
            return finish("error", None, [], error=f"{type(e).__name__}: {e}")
        except Exception as e:
            return finish("error", None, [], error=f"{type(e).__name__}: {e}")


def build_retriever(method: str = "rerank", pool: int = 30):
    """method: dense | bm25 | hybrid | rerank — all over the MM index (strategy='MM')."""
    from src.embeddings import MyEmbedder
    from src.mm.index import DOC_TITLE, OUT, STRATEGY
    from src.retrievers.bm25 import BM25Retriever
    chunks = json.loads(OUT.read_text(encoding="utf-8"))
    lex = BM25Retriever(chunks=chunks)
    if method == "bm25":
        return lex
    from src.retrievers.dense import DenseRetriever
    emb = MyEmbedder(model_name=config.EMBEDDING_MODEL, base_url=config.OLLAMA_BASE_URL, doc_title=DOC_TITLE)
    dense = DenseRetriever(embedder=emb, strategy=STRATEGY, chunks=chunks)
    if method == "dense":
        return dense
    from src.retrievers.hybrid_rrf import HybridRRFRetriever
    hyb = HybridRRFRetriever(dense=dense, lexical=lex, pool=pool)
    if method == "hybrid":
        return hyb
    from src.retrievers.rerank import RerankRetriever
    return RerankRetriever(base=hyb, pool=pool)
