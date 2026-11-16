"""Demo tab for the advanced (multimodal) challenge — NASA FY 2024 Agency Financial Report.

Sub-tabs: chat with the multimodal agent (tools search / view_page / final_answer, with crops of the cited
tables/charts/diagrams), index browser (page image vs. what was extracted), and benchmark results
(dev configurations, hand-graded test labels by group, retrieval metrics).
"""
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data/advanced/index/mm_chunks.json"
EXTRACT = ROOT / "data/advanced/extract"
BENCH = ROOT / "data/advanced/benchmark"
RES = ROOT / "results/advanced"
CHOSEN = "mmC_rerank_k5_kind_view"
CONFIGS = {
    "mmA_hybrid_k5": "A — hybrid RRF, search(query)",
    "mmB_rerank_k5_kind": "B — hybrid + rerank, search(query, kind)",
    CHOSEN: "C ★ — hybrid + rerank, search(query, kind) + view_page",
}
METHODS = {"Hybrid + rerank cross-encoder (★ đã chọn)": "rerank", "Hybrid RRF (dense + BM25)": "hybrid",
           "Dense (pgvector, embeddinggemma)": "dense", "BM25": "bm25"}
SUGGEST = [
    "Which NASA center manages the Neil A. Armstrong Test Facility, and how many civil service employees does that center have?",
    "In the FY 2024 Performance Assessment chart, how many Strategic Goal 4 performance goals were rated 'Significantly Below Target/At Risk' in FY 2024, and how many were unrated?",
    "In the 'Liabilities by Type FY 2024' donut chart, which category has the largest share, and what share and amount is it?",
    "In the land acreage table, how many Operational acres were there at the start of the prior year and at the end of the current year?",
    "In Figure 1 (NASA FMFIA Annual Statement of Assurance Process), what are the levels of the pyramid from bottom to top?",
    "How many civil service employees work at Stennis Space Center?",
]
LEDGER_CLS = None
STATUS = {"answered": "✅ trả lời", "abstain": "🚫 từ chối (thiếu evidence)", "error": "⚠️ lỗi"}


@st.cache_data
def chunks_by_id() -> dict:
    return {c["id"]: c for c in json.loads(CHUNKS.read_text(encoding="utf-8"))}


@st.cache_resource(show_spinner="Đang nạp retriever đa phương thức (pgvector + BM25 + cross-encoder)…")
def retriever(method: str):
    from src.mm.agent import build_retriever
    return build_retriever(method)


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def page_image(n: int) -> str:
    from src.mm.agent import page_png
    return str(page_png(n))


def crop_image(md: dict, page: int):
    """Saved crop if present (data/advanced/crops is git-ignored), else cut it again from the page render + bbox."""
    crop = md.get("crop")
    if crop and (ROOT / crop).exists():
        return str(ROOT / crop)
    bbox = md.get("bbox")
    if not bbox:
        return None
    from PIL import Image
    im = Image.open(page_image(page))
    W, H = im.size
    x0, y0, x1, y1 = [max(0, min(1000, float(v))) for v in bbox]
    return im.crop((int(x0 / 1000 * W), int(y0 / 1000 * H), int(x1 / 1000 * W), int(y1 / 1000 * H)))


def tools_md(r: dict) -> str:
    out = []
    for e in r.get("events", []):
        if e["event"] == "search":
            hits = ", ".join(f"p{x['page']}·{x.get('kind')}" for x in e["results"])
            out.append(f"🔎 `search(query=\"{e['query']}\", kind=\"{e.get('kind', 'any')}\")` → {hits} · {e['elapsed_ms']} ms")
        elif e["event"] == "view_page":
            out.append(f"🖼️ `view_page(page={e['page']}, focus=\"{e['focus']}\")` → [{e['label']}] · {e['elapsed_ms']} ms")
        elif e["event"] == "view_page_refused":
            out.append(f"⛔ `view_page(page={e['page']})` bị từ chối (trang chưa được search trả về)")
        elif e["event"] == "answer":
            a = e["raw"]
            out.append(f"🏁 `final_answer(abstain={str(a['abstain']).lower()}, citations={a['citations']})`")
    return "  \n".join(out) or "—"


def show_citations(r: dict, key: str):
    cmap = chunks_by_id()
    for c in r.get("citations", []):
        if "id" in c:
            ch = cmap.get(c["id"], {})
            md = ch.get("metadata", {})
            with st.expander(f"⭐ {c['id']} · trang {c['page']} (in: {c['page'] - 1}) · {md.get('kind')}", expanded=False):
                img = crop_image(md, c["page"]) if md.get("kind") != "text" else None
                if img is not None:
                    st.image(img, caption=f"Ảnh crop vùng gốc · bbox {md.get('bbox')} (0–1000)")
                st.text(ch.get("text", "")[:2500])
        else:
            with st.expander(f"⭐ ảnh trang {c['page']} (view_page)", expanded=False):
                st.image(page_image(c["page"]))


def chat_tab():
    left, right = st.columns([3, 2], gap="large")
    with right:
        st.markdown("#### ⚙️ Cấu hình agent")
        mname = st.selectbox("Retriever", list(METHODS), key="mm_method")
        k = st.select_slider("top-k mỗi lần search", options=[3, 4, 5], value=5, key="mm_k")
        view = st.checkbox("Tool `view_page` (xem ảnh trang gốc bằng vision model)", value=True, key="mm_view")
        kind = st.checkbox("Tham số `kind` trong `search` (lọc text/table/chart/diagram/map…)", value=True, key="mm_kind")
        st.caption("Mặc định = cấu hình C ★ đã chốt trên dev và chạy test 1 lần (29/30).")
        ledger = LEDGER_CLS()  # demo ledger; cap counts benchmark + demo spending
        st.caption(f"Đã chi (benchmark + demo): ${ledger.spent():.4f} / trần ${ledger.cap:.2f} · mỗi câu ~$0.001–0.003")
        if st.button("🗑️ Xóa hội thoại", key="mm_clear"):
            st.session_state["mm_chat"] = []
            st.rerun()
        st.markdown("**💡 Câu hỏi gợi ý** (dev, không lấy từ test)")
        for i, s in enumerate(SUGGEST):
            if st.button(s, key=f"mm_s{i}", width="stretch"):
                st.session_state["mm_pending"] = s

    chat = st.session_state.setdefault("mm_chat", [])
    with left:
        box = st.container(height=600)
        with box:
            if not chat:
                with st.chat_message("assistant"):
                    st.markdown("Hỏi tôi về **NASA FY 2024 Agency Financial Report** (127 trang, tiếng Anh): bảng, "
                                "biểu đồ, sơ đồ, bản đồ hay text. Tôi trả lời có trích trang và vùng gốc, và từ chối "
                                "khi tài liệu không có bằng chứng.")
            for i, m in enumerate(chat):
                if m["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(m["content"])
                    continue
                r = m["result"]
                with st.chat_message("assistant"):
                    if r["status"] == "answered":
                        st.markdown(re.sub(r"\[(nasa_p(\d{3})_[^\]]+)\]", lambda x: f" `p{int(x.group(2))}`", r["answer"]))
                    elif r["status"] == "abstain":
                        st.warning(r["answer"])
                    else:
                        st.error(r.get("error"))
                    st.markdown("**Tool agent đã gọi:**  \n" + tools_md(r))
                    st.caption(f"{STATUS[r['status']]} · {m['cfg']} · trang trích: {r.get('cited_pages')} · "
                               f"{r.get('elapsed_ms', 0) / 1000:.1f} s · ${r.get('cost_usd', 0):.5f}")
                    show_citations(r, f"c{i}")
        q = st.chat_input("Hỏi về NASA FY 2024 AFR (tiếng Anh)…", key="mm_input") or st.session_state.pop("mm_pending", None)
        if q:
            from src.llm import LLM
            from src.mm.agent import MMAgent
            chat.append({"role": "user", "content": q})
            try:
                agent = MMAgent(retriever(METHODS[mname]), LLM(ledger=ledger), top_k=k, view_page=view, kind_filter=kind)
                with box, st.chat_message("assistant"), st.spinner("Đang tìm evidence (text + bảng + hình)…"):
                    r = agent.run(q)
            except Exception as e:
                r = {"status": "error", "error": f"{type(e).__name__}: {e}", "events": [], "citations": []}
            chat.append({"role": "assistant", "result": r,
                         "cfg": f"{METHODS[mname]} · top-{k}{' · view_page' if view else ''}{' · kind' if kind else ''}"})
            st.rerun()


def index_tab():
    cmap = chunks_by_id()
    st.markdown(f"**{len(cmap)} chunk** từ **127/127 trang**. Mỗi chunk giữ trang PDF, trang in, loại, bbox và ảnh crop "
                "để đối chiếu với bản gốc.")
    kinds = pd.Series([c["metadata"]["kind"] for c in cmap.values()]).value_counts().rename("số chunk")
    st.dataframe(kinds, width=300)
    n = st.number_input("Trang PDF", 1, 127, 31)
    a, b = st.columns(2)
    with a:
        st.image(page_image(int(n)), caption=f"Trang gốc {n} (trang in {n - 1})")
    with b:
        j = jload(EXTRACT / f"p{int(n):03d}.json")
        st.caption(f"Vision ({j['usage']['model']}, {j['usage']['dpi']} dpi): {len(j['elements'])} phần tử · ${j['usage']['cost_usd']}")
        for e in j["elements"]:
            with st.expander(f"{e['kind']} · {e['title'][:70]}"):
                img = crop_image(e, int(n))
                if img is not None:
                    st.image(img)
                st.text(e["content"])
        with st.expander("Text layer (PyMuPDF)"):
            st.text(j["text_layer"])


def results_tab():
    labels = jload(RES / CHOSEN / "test/labels.json")
    if labels:
        c = st.columns(4)
        c[0].metric("Test (chấm tay)", labels["pass_rate"].split(" =")[0], labels["pass_rate"].split("= ")[1])
        c[1].metric("Ngưỡng bonus", labels["threshold"])
        c[2].metric("Lỗi hệ thống", labels["errors"])
        c[3].metric("Chi phí test", f"${labels['cost_usd']:.4f}", f"median {labels['median_s']} s")
        st.markdown("**Theo nhóm (test, cấu hình C ★):**")
        st.dataframe(pd.DataFrame([labels["by_group"]]), hide_index=True)
        df = pd.DataFrame(labels["labels"])[["id", "group", "label", "cited_pages", "reason"]]
        df["label"] = df["label"].map({"pass": "✅ đạt", "fail": "❌ không đạt"})
        st.dataframe(df, hide_index=True, width="stretch", height=420)
    st.markdown("**Dev — so sánh cấu hình (chấm tay 28 câu; auto-check chỉ là gợi ý):**")
    rows = []
    for cfg, desc in CONFIGS.items():
        s = jload(RES / cfg / "dev/summary.json")
        if s:
            rows.append({"cấu hình": desc, "dev chấm tay": "28/28", "auto-check": f"{s['auto_pass']}/{s['n']}",
                         "chi phí": f"${s['cost_usd']:.4f}", "median s": s["median_s"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    r = jload(RES / "retrieval_dev.json")
    if r:
        st.markdown("**Retrieval trên dev** (trang evidence trong top-k, dùng câu hỏi gốc làm query):")
        st.dataframe(pd.DataFrame({m: {k: v for k, v in x.items() if k != "first_evidence_rank"} for m, x in r.items()}).T)


def render(ledger_cls):
    global LEDGER_CLS
    LEDGER_CLS = ledger_cls
    st.markdown("### 🚀 Thử thách nâng cao — *NASA FY 2024 Agency Financial Report* (127 trang, public domain)")
    a, b, c = st.tabs(["💬 Chat agent đa phương thức", "🗂️ Index & đối chiếu bản gốc", "📊 Kết quả dev / test"])
    with a:
        chat_tab()
    with b:
        index_tab()
    with c:
        results_tab()
