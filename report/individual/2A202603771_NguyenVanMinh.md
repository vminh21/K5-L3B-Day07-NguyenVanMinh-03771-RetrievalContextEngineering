# Báo cáo Day 7 — Agentic RAG trên *Manifesto of the Communist Party*

MSSV: 2A202603771 · Họ tên: Nguyễn Văn Minh · Nhánh: `day7-work`

Mọi con số trong báo cáo lấy từ `results/**/summary.json`, `traces.json`, `reviews.json`, `agent_metrics.json` và `results/cost_ledger.jsonl`. Bảng chi tiết: [`results/dev_experiments.md`](../../results/dev_experiments.md), [`results/test_results.md`](../../results/test_results.md), [`results/test_v2_results.md`](../../results/test_v2_results.md), [`results/test_v3_results.md`](../../results/test_v3_results.md). Hai sửa đổi sau khi chạy được ghi riêng: [`results/gold_correction.md`](../../results/gold_correction.md) (bổ sung gold t06/u06) và [`results/metric_bugfix.md`](../../results/metric_bugfix.md) (lỗi đo Context Evidence Rate).

Dự án có **ba vòng** chọn cấu hình, mỗi vòng có tiêu chí commit trước khi đo và một bộ test mới chưa từng dùng:

| Vòng | Chỉnh trên | Chốt cấu hình | Đánh giá độc lập |
|---|---|---|---|
| 1 | dev (25) | A2 — `0a61773` | test v1 (8) |
| 2 | dev (25) | A3b — `c6ce972` | test v2 (9) |
| 3 | dev (25) + dev_hard (10) | **A2** — `89a611a` | **test v3 (26)** |

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Tài liệu: *Manifesto of the Communist Party* (Marx & Engels, bản dịch Samuel Moore 1888), PDF 2005 của Marxists Internet Archive — https://www.marxists.org/archive/marx/works/1848/communist-manifesto/.
  - Quyền sử dụng: **Public Domain**.
  - Quy mô: 44 trang; bỏ bìa còn 43 trang nội dung (2–44).
  - Chunk: index Day 6 strategy **B** (paragraph-aware, ≤1000 ký tự, overlap 0), **167 chunk**. Chi tiết trong [`data/day7/SOURCE.md`](../../data/day7/SOURCE.md).
  - Lưu ý: báo cáo Day 6 ghi 158 chunk B, nhưng DB hiện có 167; Day 7 dùng đúng nội dung trong DB. Trong 167 chunk có **7 đoạn bị lưu 2 lần** (text giống hệt, ID khác).
- **Vector store, embedding model, phiên bản và số chiều:**
  - Store: PostgreSQL 16 + pgvector **0.8.7** (Docker, cổng 55433, bảng `chunks` của Day 6), khoảng cách cosine.
  - Embedding: `embeddinggemma` qua Ollama, **768 chiều**. Giữ nguyên prefix của Day 6.
  - BM25 đọc `data/day7/chunks.json`, export từ cùng DB; đã kiểm tra hai bên cùng tập chunk ID.
  - Reranker (thử ở vòng 3, bị loại): `cross-encoder/ms-marco-MiniLM-L-6-v2`, chạy local qua sentence-transformers.
- **Agent model, cách chạy và phân chia dev/test:**
  - Model: **API `gpt-5.6-luna`** (OpenAI, Responses API), `reasoning.effort=low`.
  - Giá tính chi phí: $0.20 / $1.20 cho mỗi 1M token input/output (số liệu từ nguồn bên thứ ba).
  - Kiểm soát chi phí: trần cứng `MAX_COST_USD=1.0`; mọi lần gọi được ghi vào ledger.

| Split | Có đáp án + thiếu evidence | Ghi chú |
|---|---|---|
| dev | 22 + 3 | 22 câu Day 6 |
| dev_hard | 8 + 2 | Thêm ở vòng 3 vì dev đã bão hòa (22/22 ở mọi cấu hình). Commit `df55fb3`. |
| test v1 | 6 + 2 | Commit `5327c54`. **Không còn độc lập**: đã dùng để chẩn đoán t06. |
| test v2 | 7 + 2 | Commit `b62fa16`. Dùng cho vòng 2. |
| **test v3** | **20 + 6** | Commit `df55fb3` **trước** mọi thay đổi vòng 3; 0 chunk evidence trùng với các split khác. Chạy đúng một lần. |
| Tổng | **63 + 15** | |

- **Test v3 khó hơn ở điểm nào:** gồm các loại câu sau.
  - paraphrase (5);
  - numeric (6) — số/ngày có sẵn trong văn bản, vài câu dễ dụ model tự tính;
  - **multi-hop (3)** — cần đủ mọi nhóm evidence, lưu ở trường `gold_groups`;
  - conditional (4);
  - mục danh sách bị chunk cắt (v12);
  - chú thích của Engels (v14, v15);
  - **6 câu thiếu evidence dạng bẫy gần đúng**. Ví dụ "1888 edition" có thật nhưng không có số bản in; "3–6 năm" có thật nhưng không phải án của Marx.
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - Gold là trích nguyên văn, nằm trọn trong một chunk đúng trang (kiểm tra bằng `validate()` của starter).
  - Câu thiếu evidence có `absence_reason`, ghi cách đã grep toàn bộ 167 chunk.
  - Agent chỉ nhận `id`, `question`, `filter`; không bao giờ nhận gold.
  - Chấm tay:
    - grounded answer 0/1/2;
    - từng citation có hỗ trợ hay không;
    - abstention đúng/sai;
    - câu multi-hop chỉ được 2 điểm khi trả lời đủ mọi phần.
  - **Bổ sung gold sau khi chạy** ([`gold_correction.md`](../../results/gold_correction.md)): t06 và u06 có câu tương đương ở p41 (preface lặp nội dung). Hai câu này được thêm làm gold thay thế. Retrieval được chấm lại từ trace đã lưu, không chạy lại. Kết quả: Hit@1 test v2 tăng 5→6/7 (dense) và 6→7/7 (A2, A3b); nhãn agent không đổi.

## Retrieval và thử nghiệm

Quy ước đo:
- Context budget tính bằng **ký tự**.
- Hit@1 và Evidence Hit@3 lấy từ danh sách xếp hạng của câu hỏi gốc.
- Context Evidence Rate (CtxEv) = evidence có nằm trong context cuối hay không. Với multi-hop, Hit@k chỉ cần một evidence bắt buộc; CtxEv cần **mọi nhóm**.
- Chi phí retrieval = $0 (chạy local).

**Lỗi đo đã sửa ở vòng 3** ([`metric_bugfix.md`](../../results/metric_bugfix.md)):
- Lỗi: CtxEv bỏ sót trang của chunk neighbour, nên q06 bị tính là miss dù evidence có trong context.
- Bảng dưới dùng số **đã sửa**. Các cấu hình có neighbour, k5, ở dev tăng 21→22/22.
- Hệ quả: lý do chọn A3b ở vòng 2 ("top-k 8 nâng CtxEv 21→22") **không đúng**.

| Cấu hình | Phương pháp, top-k, rerank, budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian (median) |
|---|---|---|---|---|---|---|---|
| Tham chiếu TF-IDF starter | top-3, 800 | baseline đề | dev | 16/22 | 18/22 | 6/22 | 0.2 ms |
| **Baseline M1: Dense** | pgvector, top-5, 3000 | bắt buộc | dev | 15/22 | 18/22 | 18/22 | 46.6 ms |
| BM25 | k1=1.5 b=0.75, top-5, 3000 | bắt từ khóa hiếm | dev | 14/22 | 17/22 | 17/22 | 0.1 ms |
| Hybrid RRF | dense top-20 + BM25 top-20, RRF k=60, top-5, 3000 | hai phương pháp lỗi ở câu khác nhau | dev | 18/22 | 19/22 | 19/22 | 40.8 ms |
| Đối chứng | Hybrid, 4500, không neighbour | chỉ tăng budget có đủ không? | dev | 18/22 | 19/22 | 19/22 | 39.3 ms |
| **Cải thiện 1 (A2)** | Hybrid + **neighbour ±1**, top-5, 4500 | strategy B tách câu dẫn khỏi danh sách | dev | 18/22 | 19/22 | **22/22** | 37.3 ms |
| Cải thiện 2 (A3b, vòng 2) | + top-k 8 + gộp chunk trùng, 6000 | chunk hạng 6–8 vào context | dev | 18/22 | 19/22 | 22/22 | 37.5 ms |
| Vòng 3: rerank (A4r) — **loại** | Hybrid pool 20 → **cross-encoder** → vẫn top-5, neighbour, dedup, 4500 | đưa chunk RRF xếp thấp lên top-5 mà không tăng k | dev | 16/22 | 18/22 | **19/22** | 106.6 ms |
| Vòng 3: continuation-first — **loại** | A2 + dedup; neighbour của chunk bị cắt đi trước, neighbour khác sau mọi hit | q12: budget bị neighbour của hit hạng 1 chiếm | dev | 18/22 | 19/22 | 22/22 | 37.9 ms |
| Dense | như M1 | — | dev_hard | 3/8 | 7/8 | 6/8 | 41.3 ms |
| BM25 | như trên | — | dev_hard | 7/8 | 7/8 | 6/8 | 0.2 ms |
| Hybrid | top-5, 3000 | — | dev_hard | 7/8 | 8/8 | 7/8 | 38.9 ms |
| **A2** | như Cải thiện 1 | — | dev_hard | 7/8 | 8/8 | **8/8** | 48.3 ms |
| A4r rerank | như trên | — | dev_hard | 7/8 | 7/8 | **6/8** | 117.7 ms |
| Continuation-first | như trên | — | dev_hard | 7/8 | 8/8 | **7/8** (h04) | 37.6 ms |
| Baseline (dense) | như M1 | — | test v1 | 3/6 | 5/6 | 6/6 | 49.6 ms |
| A2 | như Cải thiện 1 | — | test v1 | 4/6 | 5/6 | 5/6 (t06) | 45.7 ms |
| Baseline (dense) | như M1 | — | test v2 | 6/7 | 7/7 | 7/7 | 45.1 ms |
| A2 / A3b | — | — | test v2 | 7/7 / 7/7 | 7/7 | 7/7 | 41.9 / 50.7 ms |
| **Baseline (dense)** | như M1 | — | **test v3** | **18/20** | **20/20** | **19/20** | 42.4 ms |
| **A2 (đã chọn)** | như Cải thiện 1 | — | **test v3** | 16/20 | 19/20 | 18/20 | 40.2 ms |
| A2 + dedup (retriever của A4) | — | — | test v3 | 16/20 | 19/20 | 18/20 | 44.0 ms |

- **Kết quả retrieval trên test v3 ngược với dev.** Trên tập test lớn nhất, **dense tốt hơn hybrid**:
  - với v01 (paraphrase), hybrid xếp gold ở hạng 7, trong khi dense xếp hạng 1;
  - cả hai đều không đưa đủ hai nhóm evidence của v16 (multi-hop) vào context.
  - Tuy vậy, ở mức agent cả hai đều đúng 20/20, vì agent tự viết lại query.
- **Rerank và t06.** Khi chẩn đoán bằng câu t06 diễn đạt lại, rerank đưa gold p37 từ hạng 10 lên hạng 2. Nhưng trên dev nó làm q12, q16, q22 rơi khỏi context. Theo tiêu chí, cải tiến làm giảm chỉ số dev thì bị loại, nên rerank bị loại.

**Lỗi dev / test, nguyên nhân, cách thử:**

| Lỗi | Hiện tượng | Nguyên nhân | Thay đổi | Trước | Sau |
|---|---|---|---|---|---|
| **E1** qn01, qn03 | Câu thiếu evidence bị trả lời kiểu *"The Manifesto does not state…"* kèm citation | Prompt v1 chỉ nói "abstain nếu thiếu evidence" | Prompt v2: abstain khi passage không trả lời **đúng câu hỏi**; cấm trả lời câu lân cận | abstention 1/3 (A0) | 3/3, 0 false abstention |
| **E2** q11, q12 | Đáp án nằm ở chunk sau câu dẫn "…the following will be pretty generally applicable:" | Strategy B tách câu dẫn khỏi danh sách | Thêm neighbour chunk, budget 4500; đối chứng chỉ tăng budget | CtxEv 19/22, 2 search/câu | **22/22** (đối chứng 19/22), 1 search |
| **E4** t06 (test v1) | Model **tự tính "1873"** từ "lived only nine years" (tài liệu ghi 1874) | Model suy luận số học trên passage | Thử bộ kiểm tra số (`src/numcheck.py`): mọi số trong câu trả lời phải có trong passage được cite; sai thì cho sửa 1 lần, sai nữa thì abstain | Prompt v3 thất bại (vòng 2) | Bắt được "1873" khi chạy offline; dev_hard h07: chặn "90%" (tự tính từ "nine-tenths") → model sửa lại đúng. **Nhưng** có false positive (xem dưới) |
| **E5** q12 (A4 dev lần 1), v07 (A4 test v3) | False abstention dù gold được retrieve ở hạng 3–5 | Neighbour của hit hạng cao chiếm hết budget 4500 trước khi tới hit hạng sau; gold bị bỏ. Phụ thuộc query model tự viết, nên dao động giữa các lần chạy | Continuation-first sửa được q12 khi replay nhưng làm h04 (multi-hop) mất evidence → loại | — | **Chưa sửa** (xem giới hạn) |

**Kiểm tra số offline** ([`numcheck_offline_replay.json`](../../results/manual/numcheck_offline_replay.json)):
- Chạy `numcheck` trên **toàn bộ 296 câu trả lời đã lưu**, không gọi LLM.
- 5 lần bị flag; chỉ **1 đúng** (t06 "1873").
- 4 sai:
  - "tenfold" được viết thành "ten times" (u07, ở 3 cấu hình);
  - "'sixties" được viết thành "1860s" (v09);
  - đại từ "one" bị đọc thành số 1.
- Không sửa bộ kiểm tra sau khi xem kết quả này, vì đó sẽ là chỉnh theo test.

**Lý do chọn cấu hình.** Mỗi vòng có tiêu chí commit trước khi đo.

- **Vòng 1** ([`selected_criteria.md`](../../configs/selected_criteria.md)): A2 thắng A1 nhờ CtxEv.
- **Vòng 2:** chọn A3b; lý do này sai do lỗi đo (xem trên).
- **Vòng 3** ([`selected_criteria_v3.md`](../../configs/selected_criteria_v3.md), `e4ef2d6`): theo yêu cầu, **top-k giữ = 5**.
  - dev_hard: A2 = A4 = A4r = 10/10.
  - dev lần 1: A2 25/25, A4 24/25 (q12).
  - Vì chênh lệch chỉ một câu do dao động, tôi viết **phụ lục** (`a7dfe33`) **trước khi** đo lần 2: chạy thêm 1 lần dev cho cả A2 và A4, quyết định theo tổng hai lần.
  - Kết quả: **A2 50/50, A4 49/50 → chọn A2** ([`selected_v3.json`](../../configs/selected_v3.json), `89a611a`).
  - A4 được khai báo trước là **ablation**: có chạy trên test v3 nhưng không được dùng để chọn.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - **Tool:** `search(query)` và `final_answer(answer, citations, abstain)`, strict schema. Model tự viết query.
  - **Nhãn passage:** chunk được đưa cho model với nhãn `[S#]`; nhãn được đổi lại thành chunk ID thật.
  - **Điều kiện dừng:**
    - có `final_answer`;
    - hoặc đạt **tối đa 3 search**;
    - citation sai → abstain;
    - lỗi DB/Ollama/API/vượt trần → `status: "error"`, không bịa câu trả lời.
  - **Kiểm tra số (chỉ A4):** từ chối câu trả lời có số không nằm trong passage được cite; cho sửa 1 lần, nếu vẫn sai thì abstain.
  - **Context:**
    - gộp chunk theo ID (A4 gộp thêm theo text);
    - budget mỗi lượt search và tổng budget;
    - không đưa lại chunk đã thấy, kể cả dưới dạng neighbour (sửa ở vòng 3; lần đo dev thứ 2 dùng bản đã sửa);
    - nội dung passage là dữ liệu, không phải chỉ dẫn.

| Cấu hình / split | Tool use | LLM / search TB | Grounded 0/1/2 (TB) | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm | Chi phí, median |
|---|---|---|---|---|---|---|---|---|
| A0 (prompt v1) / dev | 25/25 | 2.36 / 1.36 | 0/0/22 (2.00) | 34/34 | 24/24 | **1/3** | 0/22 | — |
| A2 / dev lần 1 | 25/25 | 2.24 / 1.24 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 | $0.0154, 3.6 s |
| A2 / dev lần 2 | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 30/30 | 22/22 | 3/3 | 0/22 | $0.0159, 4.9 s |
| A3 (prompt v3) / dev — loại | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 32/32 | 23/23 | **2/3** | 0/22 | — |
| A3b / dev | 25/25 | 2.20 / 1.20 | 0/0/22 (2.00) | 29/29 | 22/22 | 3/3 | 0/22 | — |
| A4 / dev lần 1 | 25/25 | 2.28 / 1.24 | **1**/0/21 (1.91) | 27/27 | 21/21 | 3/3 | **1/22** | $0.0158, 3.5 s |
| A4 / dev lần 2 | 25/25 | 2.16 / 1.16 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 | $0.0142, 4.4 s |
| A2 / dev_hard | 10/10 | 2.20 / 1.20 | 0/0/8 (2.00) | 10/10 | 8/8 | 2/2 | 0/8 | $0.0060, 4.4 s |
| A4 / dev_hard | 10/10 | 2.40 / 1.30 | 0/0/8 (2.00) | 9/9 | 8/8 | 2/2 | 0/8 | $0.0069, 4.1 s |
| A4r / dev_hard | 10/10 | 2.40 / 1.40 | 0/0/8 (2.00) | 10/10 | 8/8 | 2/2 | 0/8 | $0.0071, 4.4 s |
| A0 / test v1 | 8/8 | 2.50 / 1.50 | 0/0/6 (2.00) | 7/7 | 6/6 | 2/2 | 0/6 | — |
| A2 / test v1 | 8/8 | 2.75 / 1.62 | 0/**1**/5 (1.83) | 7/7 | 6/6 | 2/2 | 0/6 | — |
| A0 / A2 / A3b / test v2 | 9/9 | 2.2–2.4 / 1.2–1.4 | 0/0/7 (2.00) | 9/9, 9/9, 8/8 | 7/7 | 2/2 | 0/7 | — |
| **A0 / test v3** | 26/26 | 2.35 / 1.31 | 0/0/20 (2.00) | 25/25 | 20/20 | **6/6** | 0/20 | $0.0138, 4.4 s |
| **A2 (đã chọn) / test v3** | 26/26 | 2.19 / 1.19 | 0/0/20 (2.00) | 24/24 | 20/20 | **6/6** | 0/20 | $0.0150, 3.6 s |
| A4 (ablation) / test v3 | 26/26 | 2.46 / 1.38 | **1**/0/19 (1.90) | 21/21 | 19/19 | 6/6 | **1/20** (v07) | $0.0188, 3.9 s |

Lỗi hệ thống: 0 ở mọi lần chạy trong bảng. Lần chạy A2 test v1 đầu tiên lỗi DNS 8/8, được báo riêng.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q11 (dev, A2) | metadata_filter | 1 search → câu dẫn p21 hạng 1 + neighbour …e40031 | "The first measure is the abolition of property in land…" [p0021…e40031] | Grade 2; neighbour sửa E2 (A0 cần 2 search) |
| qn01 (dev, A0 → A1) | thiếu evidence | 2 search "Russian Revolution of 1917…" | A0: "The Manifesto does not state an outcome for … 1917…" [p0035…] → A1: abstain | E1, sửa bằng prompt v2 |
| t06 (test v1, A2) | paraphrase | 3 search; gold p37 ở hybrid hạng 10, không vào context | "…ended nine years later (**1873**)…" [p0041…4c2ec7][p0041…2d6d9b] | **Grade 1**: tự tính năm (E4) |
| t06 (chẩn đoán, A4, **không độc lập**) | paraphrase | 1 search "…years 1864 1872" → gold p37 …46eb1b vào context | "It began in **1864** and broke up in **1874**…" [p0037…46eb1b][p0037…b9bd5a] | Grade 2, nhưng bộ kiểm tra số **không kích hoạt**: đúng là nhờ query khác, không chứng minh được tác dụng của bộ kiểm tra |
| h07 (dev_hard, A4) | numeric | 1 search → p15 | Bản nháp "90%" bị bộ kiểm tra số từ chối → sửa thành "nine-tenths of the population" [p0015…] | Grade 2; ví dụ bộ kiểm tra số hoạt động đúng |
| v07 (test v3, A4) | numeric | 3 search; gold …f4daba ở hạng 3 và 5 nhưng không được đưa vào context | "Not enough evidence…" | **False abstention** (E5); replay cho thấy dedup và bộ kiểm tra số không phải nguyên nhân |
| v10 (test v3, A2) | multi-hop | 1 search → p35, p38 | "…'solely and exclusively to Marx' … what Darwin's theory has done for biology" [p0035…e4cf4c][p0038…745803] | Grade 2, đủ cả hai nhóm evidence |
| w06 (test v3, cả 3 cấu hình) | thiếu evidence (bẫy) | 2 search về án của Marx → p36 "seven prisoners … three to six years" | "Not enough evidence…" | Abstention đúng: không gán nhầm án 3–6 năm cho Marx |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Retrieval: `results/retrieval/<config>/<split>/`. Test v2/v3 nằm ở thư mục `*_TESTV2` / `*_TESTV3`; dev_hard ở `*_DEVHARD`.
  - Agent: `results/agent/<config>/<dev|dev_run2|dev_hard|test|test_v2|test_v3|t06_diagnostic>/{traces,reviews,summary,agent_metrics}.json`.
  - Lệnh chạy: mục *Cách chạy Day 7* trong README và `configs/selected_v3.json`. Benchmark vòng 3: `python -m src.build_benchmark --round3`.
  - Chi phí toàn dự án: **816 lần gọi API, 839 999 token input + 45 493 token output = $0.2226** (ledger), tức 22% trần $1.
    - Mỗi lần chạy dev (25 câu): $0.014–0.016.
    - Test v3 (26 câu): $0.014–0.019 mỗi cấu hình.
    - Rerank chạy local, $0, nhưng làm retrieval chậm hơn khoảng 2.5 lần (~110 ms/query).
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - *Trước/sau:*
    - A0 → A1: abstention 1/3 → 3/3.
    - A1 → A2: CtxEv dev 19 → 22/22; câu khó cần 2 → 1 search.
    - Vòng 3: rerank và continuation-first đều làm giảm chỉ số dev → loại. Bộ kiểm tra số có lúc đúng (h07, t06 offline) nhưng không cải thiện pass rate; A4 kém A2 một câu ở cả dev lẫn test v3.
  - *Test v3:* **A0 = A2 = 26/26, A4 = 25/26.**
    - Bộ test lớn và khó hơn vẫn **không phân biệt được A0 và A2** ở mức agent.
    - Ở mức retrieval, dense (baseline) còn tốt hơn hybrid (CtxEv 19 vs 18/20).
    - Kết luận trung thực: trên corpus 43 trang này, phần chính của độ chính xác đến từ agent tự viết lại query và prompt abstain (v2). Lợi ích của hybrid + neighbour chỉ thấy rõ trên dev (E2), không lặp lại trên test.
  - *Đánh đổi:*
    - Neighbour + budget 4500 tăng khoảng 16% token input (test v3: A0 49k, A2 57k).
    - A4 tăng thêm 28% (74k) do có thêm lượt sửa và search.
    - Neighbour giúp các câu bị chunk cắt (E2) nhưng gây E5: neighbour của hit hạng cao có thể đẩy hit hạng 3–5 ra khỏi budget.
  - *Giới hạn:*
    1. **Lựa chọn vòng 2 (A3b) dựa trên lỗi đo.** Sau khi sửa, A2 đã đạt 22/22, nên theo tiêu chí vòng 2 lẽ ra phải chọn A2 (rẻ hơn).
    2. **t06 chưa được sửa một cách kiểm chứng được** khi giữ top-k = 5. Rerank đưa gold lên top-5 nhưng làm hỏng dev. Bộ kiểm tra số bắt được "1873" offline nhưng có 4/5 false positive. Lần chạy chẩn đoán t06 đúng là nhờ query, và test v1 không còn độc lập.
    3. **E5 chưa sửa.** Hướng tiếp theo: luôn đưa mọi hit vào trước rồi mới tới neighbour, nhưng dành chỗ cho neighbour chứa evidence của multi-hop. Bộ kiểm tra số cần hiểu được "-fold", "'sixties" và đại từ "one". Cả hai cần được kiểm chứng trên một bộ test **mới** (test v3 đã bị xem).
    4. Kết quả dao động giữa các lần chạy (model reasoning, không có seed). Đã thấy q12 lúc đúng lúc sai với cùng cấu hình; chênh 1 câu không có ý nghĩa thống kê. Test v3 có 20 câu có đáp án, nên 1 câu = 5 điểm %.
    5. Gold được bổ sung sau khi chạy (t06, u06; với v09 thì A0 dùng evidence thay thế ở p34, chấm 2). Bổ sung này không đổi nhãn agent nào.
    6. Corpus nhỏ, tiếng Anh, chỉ có text; giá token lấy từ nguồn bên thứ ba; Day 6 có 7 chunk trùng.
    7. Nhãn do một người chấm.

## Thử thách nâng cao (nếu thực hiện)

Chưa thực hiện. Corpus hiện tại (43 trang, chỉ text) không đáp ứng yêu cầu ≥100 trang có bảng/ảnh/biểu đồ. Kế hoạch nằm trong `PLAN.md`, Bước 11.
