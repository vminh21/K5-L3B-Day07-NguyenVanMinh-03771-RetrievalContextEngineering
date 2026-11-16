"""Multimodal extraction of the NASA FY 2024 AFR (all 127 pages).

Per page:
  * text layer (PyMuPDF)            -> prose, kept verbatim
  * page render (150 dpi PNG)       -> vision model (gpt-5.6-luna, Responses API) transcribes every
                                       table / chart / diagram / map / infographic / photo into text,
                                       with a normalised bounding box (0-1000) so the crop can be checked.
Why vision for tables too: PyMuPDF find_tables() merges cells on this report (e.g. p63, p83, p114 put
whole columns in one cell), and the map (p12) and ERM figures (p39-40) are raster images with no text layer.

Outputs (cached per page, so re-runs cost nothing):
  data/advanced/extract/p{NNN}.json   vision result + text layer + usage
  data/advanced/pages/p{NNN}.png      page render (git-ignored)
  data/advanced/crops/p{NNN}_e{i}.png crop of each visual element (git-ignored)

    python -m src.mm.extract [--pages 29,65] [--dpi 150]
"""
import argparse
import base64
import json
import time
from pathlib import Path

from openai import OpenAI

from src import config
from src.llm import CostLedger, cost_of

PDF = Path("data/advanced/raw/nasa_afr_fy2024.pdf")
ROOT = Path("data/advanced")
EXTRACT, PAGES, CROPS = ROOT / "extract", ROOT / "pages", ROOT / "crops"

PROMPT = """You are indexing one page of NASA's FY 2024 Agency Financial Report for a retrieval system.
Transcribe EVERY non-prose visual element on the page so that someone who cannot see the page can answer
detailed questions about it. Elements: table, chart, diagram, map, infographic, photo.
Ignore: running body text paragraphs, page headers/footers, page numbers, QR codes, logos, decorative shapes.

For each element return:
- kind: one of table | chart | diagram | map | infographic | photo
- title: the element's title or figure number exactly as printed (or a short descriptive title)
- bbox: [x0, y0, x1, y1] in 0-1000 coordinates of the page (x to the right, y down)
- content: a complete transcription, following these rules
  * table: GitHub markdown with ALL rows and columns exactly as printed, including header rows, units
    (e.g. "in millions", "in acres", "in thousands"), blank/dash cells as "—", and row group labels.
  * chart: chart type; axis titles and units; legend mapping colour -> series; then EVERY printed value as
    one line "series | category/period | value" (e.g. "Other | FY 2023 | $106"). Also totals and percentages.
    If a value is not printed, describe what the bar/segment shows; never guess numbers.
  * diagram / map: every label; every relationship (arrows, hierarchy levels from bottom to top, which box
    connects to which, dotted vs solid lines, "managed by" links); colour legend -> meaning.
  * infographic: every number with its label and percentage.
  * photo: one sentence on what is shown plus the printed caption and photo credit if any.
Copy numbers, names and units EXACTLY as printed. Do not summarise away rows or values.
Return JSON: {"elements": [ ... ]}  (empty list if the page has only prose)."""


def page_png(doc, n: int, dpi: int) -> Path:
    PAGES.mkdir(parents=True, exist_ok=True)
    out = PAGES / f"p{n:03d}.png"
    if not out.exists():
        doc[n - 1].get_pixmap(dpi=dpi).save(out)
    return out


def crop(png: Path, n: int, i: int, bbox) -> str | None:
    from PIL import Image
    try:
        x0, y0, x1, y1 = [max(0, min(1000, float(v))) for v in bbox]
    except (TypeError, ValueError):
        return None
    if x1 - x0 < 5 or y1 - y0 < 5:
        return None
    im = Image.open(png)
    W, H = im.size
    CROPS.mkdir(parents=True, exist_ok=True)
    out = CROPS / f"p{n:03d}_e{i}.png"
    im.crop((int(x0 / 1000 * W), int(y0 / 1000 * H), int(x1 / 1000 * W), int(y1 / 1000 * H))).save(out)
    return str(out)


def run(pages: list[int], dpi: int, effort: str):
    import pymupdf
    doc = pymupdf.open(PDF)
    EXTRACT.mkdir(parents=True, exist_ok=True)
    client, ledger = OpenAI(timeout=180, max_retries=2), CostLedger()
    total = 0.0
    for n in pages:
        out = EXTRACT / f"p{n:03d}.json"
        if out.exists():
            continue
        ledger.check()
        png = page_png(doc, n, dpi)
        t0 = time.perf_counter()
        r = client.responses.create(
            model=config.LLM_MODEL, reasoning={"effort": effort}, max_output_tokens=12000, store=False,
            text={"format": {"type": "json_object"}},
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()}]}])
        u = r.usage
        c = cost_of(u.input_tokens, u.output_tokens)
        ledger.add(tag="mm_extract", model=config.LLM_MODEL, tokens_in=u.input_tokens, tokens_out=u.output_tokens,
                   reasoning_tokens=getattr(u.output_tokens_details, "reasoning_tokens", 0), cost_usd=c)
        total += c
        try:
            elements = json.loads(r.output_text).get("elements", [])
        except json.JSONDecodeError:
            elements, status = [], f"bad_json: {r.output_text[:200]}"
        else:
            status = "ok" if r.status == "completed" else r.status
        for i, e in enumerate(elements):
            e["crop"] = crop(png, n, i, e.get("bbox"))
        out.write_text(json.dumps({
            "page": n, "printed_page": n - 1, "status": status, "elements": elements,
            "text_layer": doc[n - 1].get_text(),
            "usage": {"tokens_in": u.input_tokens, "tokens_out": u.output_tokens, "cost_usd": round(c, 6),
                      "seconds": round(time.perf_counter() - t0, 1), "dpi": dpi, "effort": effort,
                      "model": config.LLM_MODEL}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"p{n:03d} {status:8s} {len(elements):2d} elements ${c:.4f} {time.perf_counter() - t0:5.1f}s "
              f"{[e.get('kind') for e in elements]}", flush=True)
    print(f"run cost ${total:.4f}; total spent ${ledger.spent():.4f} / cap ${ledger.cap:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="comma list; default all 127")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--effort", default="low")
    a = ap.parse_args()
    run([int(x) for x in a.pages.split(",")] if a.pages else list(range(1, 128)), a.dpi, a.effort)
