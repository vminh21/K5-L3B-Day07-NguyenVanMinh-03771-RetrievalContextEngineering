# Báo cáo Day 7 — Agentic RAG trên *Manifesto of the Communist Party*

| | |
|---|---|
| **MSSV** | 2A202603771 |
| **Họ tên** | Nguyễn Văn Minh |
| **Cách chạy** | [`RUN.md`](../../RUN.md) |
| **Nguồn số liệu** | `results/**/summary.json`, `traces.json`, `reviews.json`, `agent_metrics.json`, `results/cost_ledger.jsonl` |
| **Bảng chi tiết** | [`dev_experiments.md`](../../results/dev_experiments.md) · [`test_results.md`](../../results/test_results.md) (v1) · [`test_v2_results.md`](../../results/test_v2_results.md) · [`test_v3_results.md`](../../results/test_v3_results.md) |
| **Commit hash** | Lịch sử đã được viết lại một lần để bỏ dòng co-author và hoàn nguyên `README.md` của ban tổ chức; nội dung, thứ tự và thời gian commit giữ nguyên, các hash trong báo cáo là hash mới |
| **Sửa đổi sau khi chạy** | [`gold_correction.md`](../../results/gold_correction.md) (bổ sung gold t06/u06) · [`metric_bugfix.md`](../../results/metric_bugfix.md) (lỗi đo Context Evidence Rate) |

## Tóm tắt kết quả

| Câu hỏi | Trả lời ngắn |
|---|---|
| Cấu hình cuối cùng | **A2**: Hybrid RRF (dense + BM25) + neighbour chunk, top-5, budget 4500/9000 ký tự, prompt v2 |
| Kết quả test độc lập lớn nhất (test v3, 26 câu) | A2 **26/26** · baseline A0 **26/26** · A4 (ablation) 25/26 |
| Retrieval trên test v3 (Context Evidence Rate) | Dense 19/20 · A2 18/20 |
| Cải thiện rõ nhất | Prompt v2 (abstention 1/3 → 3/3); neighbour chunk (Context Evidence Rate dev 19 → 22/22) |
| Lỗi chưa sửa | t06 (model tự tính năm), E5 (neighbour đẩy hit hạng 3–5 khỏi budget) |
| Tổng chi phí API | **$0.2226** / trần $1 (816 lần gọi) |
| Bonus nâng cao | Chưa thực hiện |

## Dữ liệu và benchmark

**Nguồn, quyền sử dụng, số trang và số chunk**

| Mục | Giá trị |
|---|---|
| Tài liệu | *Manifesto of the Communist Party* (Marx & Engels, bản dịch Samuel Moore 1888), PDF 2005 của Marxists Internet Archive |
| Link | https://www.marxists.org/archive/marx/works/1848/communist-manifesto/ |
| Quyền sử dụng | **Public Domain** ([`data/day7/SOURCE.md`](../../data/day7/SOURCE.md)) |
| Số trang | 44 trang; bỏ bìa → **43 trang nội dung** (2–44) |
| Chunk | Day 6 strategy **B** (paragraph-aware, ≤ 1000 ký tự, overlap 0) → **167 chunk** |
| Lưu ý dữ liệu | Báo cáo Day 6 ghi 158 chunk B, DB hiện có 167. Có **7 đoạn bị lưu 2 lần** (text giống, ID khác) |

**Vector store, embedding model, phiên bản và số chiều**

| Thành phần | Giá trị |
|---|---|
| Vector store | PostgreSQL 16 + pgvector **0.8.7** (Docker, cổng 55433, bảng `chunks` của Day 6), cosine |
| Embedding | `embeddinggemma` qua Ollama, **768 chiều**, giữ nguyên prefix Day 6 |
| BM25 | Đọc `data/day7/chunks.json` export từ cùng DB (đã kiểm tra cùng tập chunk ID) |
| Reranker (vòng 3, bị loại) | `cross-encoder/ms-marco-MiniLM-L-6-v2`, local |

**Agent model, cách chạy và phân chia dev/test**

| Mục | Giá trị |
|---|---|
| Model | API **`gpt-5.6-luna`** (OpenAI Responses API), `reasoning.effort=low` |
| Giá tính chi phí | $0.20 / $1.20 mỗi 1M token input / output (nguồn bên thứ ba) |
| Kiểm soát chi phí | Trần cứng `MAX_COST_USD=1.0`; mọi lần gọi ghi vào `results/cost_ledger.jsonl` |
| Cách chạy | [`RUN.md`](../../RUN.md) |

| Split | Có đáp án | Thiếu evidence | Commit | Vai trò |
|---|---:|---:|---|---|
| dev | 22 | 3 | `e70e0a3` | Chỉnh và chọn cấu hình (22 câu Day 6) |
| dev_hard | 8 | 2 | `e6e0513` | Chỉnh vòng 3 (dev cũ đã bão hòa 22/22) |
| test v1 | 6 | 2 | `e70e0a3` | Đánh giá vòng 1 — **không còn độc lập** (đã dùng để chẩn đoán t06) |
| test v2 | 7 | 2 | `6fa2c93` | Đánh giá vòng 2 |
| **test v3** | **20** | **6** | `e6e0513` | Đánh giá vòng 3, chạy đúng 1 lần |
| **Tổng** | **63** | **15** | | |

**Test v3 — loại câu** (0 chunk evidence trùng với các split khác; commit trước mọi thay đổi vòng 3)

| Loại | Số câu | Ví dụ / độ khó |
|---|---:|---|
| Paraphrase | 5 | Ít trùng từ khóa với văn bản |
| Numeric | 6 | Số/ngày có trong văn bản; vài câu dụ model tự tính |
| Multi-hop | 3 | Cần **đủ mọi nhóm evidence** (`gold_groups`) |
| Conditional | 4 | "Ở Đức, khi nào… chống lại ai?" |
| Metadata filter | 1 | Mục danh sách bị chunk cắt (v12) |
| Direct (chú thích) | 1 | Chú thích của Engels (v14) |
| Thiếu evidence (bẫy) | 6 | "1888 edition" có thật nhưng không có số bản in; "3–6 năm" có thật nhưng không phải án của Marx |

**Cách xác định câu có/thiếu evidence và tiêu chí chấm**

| Mục | Quy định |
|---|---|
| Gold | Trích nguyên văn, nằm trọn trong 1 chunk đúng trang (`validate()` của starter); đoạn lặp ở nhiều preface ghi thành gold thay thế |
| Câu thiếu evidence | `absence_reason` ghi cách grep toàn bộ 167 chunk |
| Agent nhận | Chỉ `id`, `question`, `filter` — không bao giờ nhận gold |
| Grounded answer | 0 = sai / thiếu evidence · 1 = đúng một phần · 2 = đúng và đủ; multi-hop phải đủ mọi phần mới được 2 |
| Citation | Đọc từng chunk được cite, chấm có hỗ trợ hay không |
| Abstention | Kiểm tra agent thực sự từ chối, không thêm khẳng định |
| Bổ sung gold sau khi chạy | t06, u06 có câu tương đương ở p41 → thêm làm gold thay thế; retrieval chấm lại **từ trace đã lưu**; không đổi nhãn agent |

## Retrieval và thử nghiệm

**Quy ước đo**

| Chỉ số | Định nghĩa |
|---|---|
| Context budget | Đo bằng **ký tự** (gồm header của chunk) |
| Hit@1 / Evidence Hit@3 | Theo danh sách xếp hạng của **câu hỏi gốc**; multi-hop: chỉ cần một evidence bắt buộc |
| Context Evidence Rate (CtxEv) | Evidence nằm trong context cuối; multi-hop: cần **mọi nhóm** |
| Chi phí retrieval | $0 (chạy local) |
| Lỗi đo đã sửa | CtxEv từng bỏ sót trang của chunk neighbour → bảng dưới dùng số **đã sửa** ([`metric_bugfix.md`](../../results/metric_bugfix.md)) |

**Dev (22 câu có đáp án)**

| Cấu hình | Phương pháp, top-k, rerank, budget | Giả thuyết / thay đổi | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian |
|---|---|---|---|---|---|---|
| Tham chiếu TF-IDF starter | top-3, 800 | Baseline của đề | 16/22 (72.7%) | 18/22 (81.8%) | 6/22 (27.3%) | 0.2 ms |
| **Baseline M1: Dense** | pgvector, top-5, 3000 | Bắt buộc | 15/22 (68.2%) | 18/22 (81.8%) | 18/22 (81.8%) | 46.6 ms |
| Phương pháp 2: BM25 | k1=1.5 b=0.75, top-5, 3000 | Bắt từ khóa hiếm | 14/22 (63.6%) | 17/22 (77.3%) | 17/22 (77.3%) | 0.1 ms |
| Phương pháp 3: Hybrid RRF | dense top-20 + BM25 top-20, RRF k=60, top-5, 3000 | Hai phương pháp lỗi ở câu khác nhau | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 40.8 ms |
| Đối chứng | Hybrid, 4500, không neighbour | Chỉ tăng budget có đủ không? | 18/22 | 19/22 | 19/22 (86.4%) | 39.3 ms |
| **Cải thiện 1 (A2, chọn)** | Hybrid + **neighbour ±1**, top-5, 4500 | Strategy B tách câu dẫn khỏi danh sách | 18/22 | 19/22 | **22/22 (100%)** | 37.3 ms |
| Cải thiện 2 (A3b, vòng 2) | + top-k 8 + gộp chunk trùng, 6000 | Chunk hạng 6–8 vào context | 18/22 | 19/22 | 22/22 (100%) | 37.5 ms |
| Rerank (A4r) — **loại** | Hybrid pool 20 → cross-encoder → top-5, 4500 | Đưa chunk RRF xếp thấp lên mà không tăng k | 16/22 (72.7%) | 18/22 (81.8%) | **19/22 (86.4%)** | 106.6 ms |
| Continuation-first — **loại** | A2 + dedup; neighbour của chunk bị cắt đi trước | Budget bị neighbour của hit hạng 1 chiếm | 18/22 | 19/22 | 22/22 (100%) | 37.9 ms |

**Dev khó — dev_hard (8 câu có đáp án)**

| Cấu hình | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian |
|---|---|---|---|---|
| Dense | 3/8 (37.5%) | 7/8 (87.5%) | 6/8 (75.0%) | 41.3 ms |
| BM25 | 7/8 (87.5%) | 7/8 (87.5%) | 6/8 (75.0%) | 0.2 ms |
| Hybrid | 7/8 (87.5%) | 8/8 (100%) | 7/8 (87.5%) | 38.9 ms |
| **A2** | 7/8 (87.5%) | 8/8 (100%) | **8/8 (100%)** | 48.3 ms |
| Rerank (A4r) | 7/8 (87.5%) | 7/8 (87.5%) | **6/8 (75.0%)** | 117.7 ms |
| Continuation-first | 7/8 (87.5%) | 8/8 (100%) | **7/8 (87.5%)** (h04) | 37.6 ms |

**Test (sau khi chốt)**

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian |
|---|---|---|---|---|---|
| Baseline (dense) | test v1 | 3/6 (50.0%) | 5/6 (83.3%) | 6/6 (100%) | 49.6 ms |
| A2 (chọn vòng 1) | test v1 | 4/6 (66.7%) | 5/6 (83.3%) | 5/6 (83.3%) — miss t06 | 45.7 ms |
| Baseline (dense) | test v2 | 6/7 (85.7%) | 7/7 (100%) | 7/7 (100%) | 45.1 ms |
| A2 | test v2 | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 41.9 ms |
| A3b (chọn vòng 2) | test v2 | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 50.7 ms |
| **Baseline (dense)** | **test v3** | **18/20 (90.0%)** | **20/20 (100%)** | **19/20 (95.0%)** — miss v16 | 42.4 ms |
| **A2 (chọn vòng 3)** | **test v3** | 16/20 (80.0%) | 19/20 (95.0%) | 18/20 (90.0%) — miss v01, v16 | 40.2 ms |
| A2 + dedup (retriever A4) | test v3 | 16/20 (80.0%) | 19/20 (95.0%) | 18/20 (90.0%) | 44.0 ms |

Hybrid RRF vừa là phương pháp 3 vừa là cải thiện so với dense. Trên test v3, **dense tốt hơn hybrid**: ở v01 (paraphrase) hybrid xếp gold hạng 7, dense hạng 1. Ở mức agent cả hai vẫn 20/20 vì agent tự viết lại query.

**Lỗi, nguyên nhân, cách thử**

| Lỗi | Hiện tượng | Nguyên nhân | Thay đổi | Trước | Sau |
|---|---|---|---|---|---|
| **E1** qn01, qn03 (dev) | Câu thiếu evidence bị trả lời "The Manifesto does not state…" kèm citation | Prompt v1 chỉ nói "abstain nếu thiếu" | Prompt v2: abstain khi passage không trả lời **đúng câu hỏi** | Abstention 1/3 | **3/3**, 0 từ chối nhầm |
| **E2** q11, q12 (dev) | Đáp án ở chunk sau câu dẫn "…the following will be pretty generally applicable:" | Strategy B tách câu dẫn khỏi danh sách | Neighbour chunk, budget 4500; đối chứng chỉ tăng budget | CtxEv 19/22, 2 search/câu | **22/22** (đối chứng 19/22), 1 search |
| **E4** t06 (test v1) | Model **tự tính "1873"** (tài liệu ghi 1874) | Suy luận số học trên passage | Bộ kiểm tra số `src/numcheck.py` | Prompt v3 thất bại (vòng 2) | Bắt được "1873" offline; chặn "90%" ở h07. **Nhưng** nhiều báo nhầm (bảng dưới) |
| **E5** q12 (A4 dev lần 1), v07 (A4 test v3) | Từ chối nhầm dù gold được retrieve hạng 3–5 | Neighbour của hit hạng cao chiếm hết budget 4500 | Continuation-first | — | Sửa q12 nhưng làm hỏng h04 → loại; **chưa sửa** |

**Bộ kiểm tra số — chạy offline trên 296 câu trả lời đã lưu** ([`numcheck_offline_replay.json`](../../results/manual/numcheck_offline_replay.json))

| Trường hợp bị flag | Số | Đúng / nhầm | Lý do |
|---|---|---|---|
| A2 / test v1 / t06 | 1873 | **Đúng** | Tài liệu ghi 1874 |
| A2 / test v1 / t06 | 1 | Nhầm | Đại từ "one" bị đọc thành số |
| u07 (test v2, 3 cấu hình) | 10 | Nhầm | "tenfold" → "ten times" |
| A0 / test v3 / v09 | 1860 | Nhầm | "'sixties" → "1860s" |
| **Tổng** | | **1 đúng / 4 nhầm** | Không sửa sau khi xem (sẽ là chỉnh theo test) |

**Lý do chọn cấu hình** (tiêu chí commit trước khi đo ở mọi vòng)

| Vòng | Tiêu chí | Ứng viên và kết quả | Chọn | Commit |
|---|---|---|---|---|
| 1 | [`selected_criteria.md`](../../configs/selected_criteria.md): pass dev → CtxEv → Hit@3 → citation → rẻ/nhanh | A1 = A2 = 25/25; CtxEv A2 cao hơn | **A2** | `2f28739` |
| 2 | [`selected_criteria_v2.md`](../../configs/selected_criteria_v2.md) | A3b 25/25, CtxEv 22/22 (A3 prompt v3 bị loại: abstention 2/3) | A3b — **sai do lỗi đo**: A2 thực ra cũng 22/22 → lẽ ra chọn A2 (rẻ hơn) | `af9cdc7` |
| 3 | [`selected_criteria_v3.md`](../../configs/selected_criteria_v3.md): top-k giữ = 5; pass dev_hard → pass dev → CtxEv | dev_hard: A2 = A4 = A4r = 10/10. Dev 2 lần (theo phụ lục `9a22c64`, viết trước lần đo 2): A2 **50/50**, A4 49/50. Rerank, continuation-first bị loại vì giảm CtxEv dev | **A2** (A4 = ablation khai báo trước) | `7b8354e` |

## Agent và đánh giá

**Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi**

| Thành phần | Thiết kế |
|---|---|
| Tool | `search(query)` và `final_answer(answer, citations, abstain)`, strict schema; model tự viết query |
| Nhãn passage | Chunk đưa cho model với nhãn `[S#] (page, chapter)`; đổi lại thành chunk ID thật trong câu trả lời và trace |
| Số lượt | Tối đa **3 search**; trung bình thực tế 1.2–1.4 search, 2.2–2.5 lần gọi LLM mỗi câu |
| Điều kiện dừng | `final_answer` · đủ 3 search (buộc trả lời / abstain) · citation sai → abstain |
| Lỗi hệ thống | Lỗi DB / Ollama / API / vượt trần chi phí → `status: "error"`, không bịa câu trả lời, batch chạy tiếp |
| Context | Gộp chunk theo ID (A4 gộp thêm theo text); budget mỗi lượt và tổng; không đưa lại chunk đã thấy, kể cả làm neighbour; neighbour ±1 chunk ở A2 |
| Kiểm tra số (chỉ A4) | Số trong câu trả lời phải có trong passage được cite; sai → sửa 1 lần → vẫn sai thì abstain |
| An toàn | Nội dung passage là dữ liệu, không phải chỉ dẫn (chống prompt injection) |

**Kết quả agent** (chấm tay từng câu)

| Cấu hình / split | Tool use | Số lượt gọi TB (LLM / search) | Grounded 0/1/2 (TB) | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| A0 (prompt v1) / dev | 25/25 | 2.36 / 1.36 | 0/0/22 (2.00) | 34/34 | 24/24 | **1/3** | 0/22 |
| A2 / dev lần 1 | 25/25 | 2.24 / 1.24 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 |
| A2 / dev lần 2 | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 30/30 | 22/22 | 3/3 | 0/22 |
| A3 (prompt v3) / dev — loại | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 32/32 | 23/23 | **2/3** | 0/22 |
| A3b / dev | 25/25 | 2.20 / 1.20 | 0/0/22 (2.00) | 29/29 | 22/22 | 3/3 | 0/22 |
| A4 / dev lần 1 | 25/25 | 2.28 / 1.24 | **1**/0/21 (1.91) | 27/27 | 21/21 | 3/3 | **1/22** |
| A4 / dev lần 2 | 25/25 | 2.16 / 1.16 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 |
| A2 / dev_hard | 10/10 | 2.20 / 1.20 | 0/0/8 (2.00) | 10/10 | 8/8 | 2/2 | 0/8 |
| A4 / dev_hard | 10/10 | 2.40 / 1.30 | 0/0/8 (2.00) | 9/9 | 8/8 | 2/2 | 0/8 |
| A4r / dev_hard | 10/10 | 2.40 / 1.40 | 0/0/8 (2.00) | 10/10 | 8/8 | 2/2 | 0/8 |
| A0 / test v1 | 8/8 | 2.50 / 1.50 | 0/0/6 (2.00) | 7/7 | 6/6 | 2/2 | 0/6 |
| A2 / test v1 | 8/8 | 2.75 / 1.62 | 0/**1**/5 (1.83) | 7/7 | 6/6 | 2/2 | 0/6 |
| A0 / test v2 | 9/9 | 2.44 / 1.44 | 0/0/7 (2.00) | 9/9 | 7/7 | 2/2 | 0/7 |
| A2 / test v2 | 9/9 | 2.22 / 1.22 | 0/0/7 (2.00) | 9/9 | 7/7 | 2/2 | 0/7 |
| A3b / test v2 | 9/9 | 2.22 / 1.22 | 0/0/7 (2.00) | 8/8 | 7/7 | 2/2 | 0/7 |
| **A0 / test v3** | 26/26 | 2.35 / 1.31 | 0/0/20 (2.00) | 25/25 | 20/20 | **6/6** | 0/20 |
| **A2 (chọn) / test v3** | 26/26 | 2.19 / 1.19 | 0/0/20 (2.00) | 24/24 | 20/20 | **6/6** | 0/20 |
| A4 (ablation) / test v3 | 26/26 | 2.46 / 1.38 | **1**/0/19 (1.90) | 21/21 | 19/19 | 6/6 | **1/20** (v07) |

Lỗi hệ thống: 0 ở mọi lần chạy trong bảng. Lần chạy A2 test v1 đầu tiên lỗi DNS 8/8 (`APIConnectionError`, $0), trace giữ ở `results/agent/A2_hybrid_v2_nb/test_attempt1_connection_error/`, chạy lại đúng một lần.

**Ví dụ từng câu**

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q11 (dev, A2) | metadata_filter | 1 search → câu dẫn p21 hạng 1 + neighbour …e40031 | "The first measure is the abolition of property in land…" [p0021…e40031] | Grade 2; neighbour sửa E2 (A0 cần 2 search) |
| qn01 (dev, A0 → A1) | thiếu evidence | 2 search "Russian Revolution of 1917…" | A0: "The Manifesto does not state an outcome for … 1917…" [p0035…] → A1: abstain | E1, sửa bằng prompt v2 |
| t06 (test v1, A2) | paraphrase | 3 search; gold p37 ở hybrid hạng 10, không vào context | "…ended nine years later (**1873**)…" [p0041…4c2ec7][p0041…2d6d9b] | **Grade 1**: tự tính năm (E4) |
| t06 (chẩn đoán, A4, **không độc lập**) | paraphrase | 1 search "…years 1864 1872" → gold p37 …46eb1b vào context | "It began in **1864** and broke up in **1874**…" [p0037…46eb1b][p0037…b9bd5a] | Grade 2, nhưng bộ kiểm tra số **không kích hoạt** — đúng nhờ query khác |
| h07 (dev_hard, A4) | numeric | 1 search → p15 | Bản nháp "90%" bị từ chối → sửa thành "nine-tenths of the population" [p0015…] | Grade 2; bộ kiểm tra số hoạt động đúng |
| v07 (test v3, A4) | numeric | 3 search; gold …f4daba hạng 3 và 5 nhưng không vào context | "Not enough evidence…" | **Từ chối nhầm** (E5); replay: không do dedup hay bộ kiểm tra số |
| v10 (test v3, A2) | multi-hop | 1 search → p35, p38 | "…'solely and exclusively to Marx' … what Darwin's theory has done for biology" [p0035…e4cf4c][p0038…745803] | Grade 2, đủ cả hai nhóm evidence |
| w06 (test v3, cả 3 cấu hình) | thiếu evidence (bẫy) | 2 search về án của Marx → p36 "seven prisoners … three to six years" | "Not enough evidence…" | Abstention đúng: không gán án 3–6 năm cho Marx |

**Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí**

| Mục | Vị trí / giá trị |
|---|---|
| Trace retrieval | `results/retrieval/<config>/<split>/` (thư mục `*_TESTV2`, `*_TESTV3`, `*_DEVHARD`) |
| Trace, nhãn, metric agent | `results/agent/<config>/<split>/{traces,reviews,summary,agent_metrics}.json` |
| Context chấm tay | `results/manual/context_review_test*.json` |
| Lệnh chạy | [`RUN.md`](../../RUN.md); cấu hình chốt [`configs/selected_v3.json`](../../configs/selected_v3.json) |

| Chạy | Chi phí | Median latency | Token input |
|---|---|---|---|
| Agent dev, 25 câu (mỗi lần) | $0.014–0.016 | 3.5–4.9 s/câu | 53–60k |
| Agent dev_hard, 10 câu | $0.006–0.007 | 4.1–4.4 s/câu | 22–27k |
| A0 / test v3 | $0.0138 | 4.4 s/câu | 49k |
| A2 / test v3 | $0.0150 | 3.6 s/câu | 57k |
| A4 / test v3 | $0.0188 | 3.9 s/câu | 74k |
| Retrieval dense / hybrid / BM25 / rerank | $0 | 40–50 / 37–48 / 0.1 / 107–118 ms | — |
| **Toàn dự án** | **$0.2226** (816 lần gọi; 839 999 in + 45 493 out) | | |

**Kết quả trước/sau, đánh đổi và giới hạn**

| Thay đổi | Trước → sau | Kết luận |
|---|---|---|
| Prompt v1 → v2 (A0 → A1) | Abstention 1/3 → 3/3 | Giữ |
| + Neighbour (A1 → A2) | CtxEv dev 19 → 22/22; câu khó 2 → 1 search | Giữ |
| Prompt v3 (A3) | Abstention 3/3 → 2/3 | Loại |
| Top-k 8 (A3b) | Không hơn A2 sau khi sửa lỗi đo | Không cần |
| Rerank (A4r) | CtxEv dev 22 → 19, dev_hard 8 → 6 | Loại |
| Continuation-first | CtxEv dev_hard 8 → 7 | Loại |
| Bộ kiểm tra số + dedup (A4) | Dev 49/50 vs A2 50/50; test v3 25/26 vs 26/26 | Không chọn |

| Đánh đổi | Số liệu |
|---|---|
| Neighbour + budget 4500 | Token input +16% (test v3: A0 49k → A2 57k), nhưng ít search hơn ở câu khó |
| A4 | Token input +28% so với A2 (74k), do thêm lượt sửa và search |
| Rerank | Chậm hơn ~2.5 lần (~110 ms/query), $0 |
| Neighbour | Giúp câu bị chunk cắt (E2) nhưng gây E5 (đẩy hit hạng 3–5 khỏi budget) |

| # | Giới hạn |
|---|---|
| 1 | **Test v3: A0 = A2 = 26/26** — bộ test lớn và khó hơn vẫn không phân biệt được baseline với cấu hình chọn; retrieval dense còn tốt hơn. Phần chính của độ chính xác đến từ agent tự viết lại query và prompt v2; lợi ích của hybrid + neighbour chỉ rõ trên dev |
| 2 | Lựa chọn vòng 2 (A3b) dựa trên lỗi đo |
| 3 | **t06 chưa sửa được một cách kiểm chứng** khi giữ top-k = 5: rerank hỏng dev; bộ kiểm tra số 4/5 báo nhầm; lần chạy chẩn đoán đúng nhờ query; test v1 không còn độc lập |
| 4 | E5 chưa sửa. Hướng tiếp: luôn đưa mọi hit trước neighbour nhưng chừa chỗ cho neighbour multi-hop; bộ kiểm tra số hiểu "-fold", "'sixties", "one" — cần kiểm chứng trên bộ test **mới** |
| 5 | Kết quả dao động giữa các lần chạy (không có seed); 1 câu test v3 = 5 điểm %, chênh 1 câu không có ý nghĩa thống kê |
| 6 | Gold bổ sung sau khi chạy (t06, u06; v09 của A0 dùng evidence thay thế ở p34) — không đổi nhãn agent |
| 7 | Corpus nhỏ, tiếng Anh, chỉ text; giá token từ nguồn bên thứ ba; Day 6 có 7 chunk trùng; nhãn do một người chấm |

## Thử thách nâng cao (nếu thực hiện)

| Mục | Trạng thái |
|---|---|
| Thực hiện | **Chưa** |
| Lý do | Corpus hiện tại 43 trang, chỉ text — không đạt yêu cầu ≥ 100 trang có bảng, ảnh, biểu đồ |
| Kế hoạch | `PLAN.md`, Bước 11 (index riêng `mm_chunks`) |
