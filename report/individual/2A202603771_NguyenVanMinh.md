# Báo cáo Day 7 — Agentic RAG trên *Manifesto of the Communist Party*

MSSV: 2A202603771 · Họ tên: Nguyễn Văn Minh · Nhánh: `day7-work`

Mọi con số trong báo cáo lấy từ `results/**/summary.json`, `traces.json`, `reviews.json`, `agent_metrics.json` và `results/cost_ledger.jsonl`. Bảng tổng hợp chi tiết: [`results/dev_experiments.md`](../../results/dev_experiments.md), [`results/test_results.md`](../../results/test_results.md), [`results/test_v2_results.md`](../../results/test_v2_results.md).

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:** *Manifesto of the Communist Party* (Marx & Engels, bản dịch Samuel Moore 1888), bản PDF 2005 của Marxists Internet Archive — https://www.marxists.org/archive/marx/works/1848/communist-manifesto/ — **Public Domain**. 44 trang, bỏ trang bìa → 43 trang nội dung (2–44). Index Day 6 strategy **B** (paragraph-aware, ≤1000 ký tự, overlap 0): **167 chunk**. Chi tiết: [`data/day7/SOURCE.md`](../../data/day7/SOURCE.md).
  - Lưu ý dữ liệu: báo cáo Day 6 ghi 158 chunk B nhưng DB hiện có 167; Day 7 dùng đúng nội dung DB. Trong 167 chunk có **7 đoạn bị lưu 2 lần** (text giống hệt, ID khác) — phát hiện ở vòng 2 và xử lý bằng gộp chunk trùng (I1).
- **Vector store, embedding model, phiên bản và số chiều:** PostgreSQL 16 + pgvector **0.8.7** (Docker `pgvector/pgvector:0.8.7-pg16`, cổng 55433, bảng `chunks` của Day 6), cosine. Embedding `embeddinggemma` qua Ollama local, **768 chiều**, prefix giữ nguyên Day 6 (document `title: … | text: …`, query `task: search result | query: …`). Dense đọc trực tiếp DB; BM25 đọc `data/day7/chunks.json` export từ cùng DB (`src/export_day6.py`), đã kiểm tra cùng tập chunk ID.
- **Agent model, cách chạy và phân chia dev/test:** **API `gpt-5.6-luna`** (OpenAI, Responses API — model này không nhận function tools qua Chat Completions), `reasoning.effort=low`, `max_output_tokens=1500`, không đặt temperature (model reasoning). Giá dùng để tính chi phí: $0.20 / $1.20 mỗi 1M token input/output (theo nguồn bên thứ ba, cần đối chiếu trang giá OpenAI). Trần chi phí cứng `MAX_COST_USD=1.0`, mọi lần gọi ghi vào `results/cost_ledger.jsonl`.
  - **Dev:** 22 câu có đáp án (toàn bộ 22 câu Day 6; q18–q22 là test Day 6 nhưng đã bị xem kết quả nên chuyển sang dev) + 3 câu thiếu evidence (qn01–qn03).
  - **Test v1:** 6 câu mới + 2 câu thiếu evidence, trang chưa dùng ở Day 6; commit đóng băng `5327c54` trước mọi thí nghiệm.
  - **Test v2:** 7 câu mới + 2 câu thiếu evidence, trang chưa dùng ở dev/test v1; viết và commit (`b62fa16`) **sau khi test v1 đã bị dùng để chẩn đoán lỗi t06** và **trước** mọi thay đổi vòng 2 (xem phần giới hạn).
  - Tổng: **35 câu có đáp án + 7 câu thiếu evidence**.
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:** câu có đáp án có `gold` = trích nguyên văn nằm trọn trong một chunk đúng trang (qua `validate()` của starter; đoạn lặp ở nhiều preface được ghi thành gold thay thế). Câu thiếu evidence có `absence_reason` ghi cách kiểm tra toàn corpus (grep từ khóa trên 167 chunk, ví dụ `1917/Lenin/Bolshevik` = 0; `1818` chỉ là năm của Lewis Henry Morgan). Agent chỉ nhận `id`, `question`, `filter`; không bao giờ nhận gold. Chấm thủ công: grounded answer 0/1/2 (0 = sai/thiếu evidence, 1 = đúng một phần, 2 = đúng và đủ), từng citation có hỗ trợ không, abstention đúng/sai; context test 0/1/2.

## Retrieval và thử nghiệm

Context budget đo bằng **ký tự** (gồm header `[chunk_id | source | page | chapter]`). Hit@1 / Evidence Hit@3 lấy từ danh sách xếp hạng của **câu hỏi gốc** (không rewrite); Context Evidence Rate = evidence nằm trong context cuối. Chi phí retrieval = $0 (chạy local).

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian (median) / chi phí |
|---|---|---|---|---|---|---|---|
| Tham chiếu: TF-IDF starter | lexical, top-3, no filter, 800 ký tự | baseline của đề | dev | 16/22 (72.7%) | 18/22 (81.8%) | 6/22 (27.3%) | 0.2 ms / $0 |
| **Baseline M1: Dense** | pgvector Day 6, top-5, no filter, không rerank, 3000 | phương pháp bắt buộc | dev | 15/22 (68.2%) | 18/22 (81.8%) | 18/22 (81.8%) | 46.6 ms / $0 |
| Phương pháp 2: BM25 | Okapi k1=1.5 b=0.75, stopword EN, top-5, 3000 | bắt từ khóa hiếm | dev | 14/22 (63.6%) | 17/22 (77.3%) | 17/22 (77.3%) | 0.1 ms / $0 |
| Phương pháp 3: Hybrid RRF | dense top-20 + BM25 top-20, RRF k=60 (theo rank), top-5, 3000 | dense và BM25 lỗi ở câu khác nhau | dev | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 40.8 ms / $0 |
| Đối chứng | Hybrid, top-5, budget 4500, không neighbour | budget lớn hơn có đủ không? | dev | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 39.3 ms / $0 |
| **Cải thiện 1** (chọn vòng 1) | Hybrid + **neighbour chunk** (±1 chunk liền kề), top-5, 4500 | E2: strategy B tách câu dẫn khỏi danh sách | dev | 18/22 (81.8%) | 19/22 (86.4%) | **21/22 (95.5%)** | 44.1 ms / $0 |
| **Cải thiện 2** (chọn vòng 2) | Cải thiện 1 + **top-k 8** + **gộp chunk trùng text**, 6000 | chunk đúng ở hạng 6–8 vào context; bản sao không chiếm chỗ | dev | 18/22 (81.8%) | 19/22 (86.4%) | **22/22 (100%)** | 45.9 ms / $0 |
| Baseline (dense) | như M1 | — | test v1 | 3/6 (50.0%) | 5/6 (83.3%) | 6/6 (100%) | 49.6 ms / $0 |
| Cấu hình đã chọn vòng 1 | như Cải thiện 1 | — | test v1 | 4/6 (66.7%) | 5/6 (83.3%) | **5/6 (83.3%)** | 45.7 ms / $0 |
| Baseline (dense) | như M1 | — | test v2 | 5/7 (71.4%) | 7/7 (100%) | 7/7 (100%) | 45.1 ms / $0 |
| Cấu hình chọn vòng 1 | như Cải thiện 1 | — | test v2 | 6/7 (85.7%) | 7/7 (100%) | 7/7 (100%) | 41.9 ms / $0 |
| Cấu hình chọn vòng 2 | như Cải thiện 2 | — | test v2 | 6/7 (85.7%) | 7/7 (100%) | 7/7 (100%) | 50.7 ms / $0 |

Hybrid RRF vừa là phương pháp 3 vừa là cải thiện so với dense. Filter chương (lấy từ trường `filter` của câu hỏi, coi như người dùng cung cấp — 4 câu dev) gần như không đổi kết quả (chỉ dense: context 18 → 19/22). Context thủ công trên test: v1 dense 6× mức 2; hybrid + neighbour 5× mức 2, 1× mức 0 (t06). Test v2: cả hai 7× mức 2 ([`results/manual/`](../../results/manual/)).

**Hai lỗi dev, nguyên nhân, cách thử:**

| Lỗi | Hiện tượng | Nguyên nhân | Thay đổi | Trước | Sau |
|---|---|---|---|---|---|
| **E1** qn01, qn03 | Câu thiếu evidence nhưng agent trả `answered`: *"The Manifesto does not state…"* rồi trả lời một câu lân cận (preface 1882 về Nga; lương = chi phí sinh tồn) kèm citation | Prompt v1 chỉ nói "abstain nếu thiếu evidence"; model coi việc *nói* là thiếu rồi trả lời phần liên quan là hữu ích | Prompt v2: chỉ đổi luật 4 — abstain khi passage không trả lời **đúng câu hỏi**, cấm kiểu "tài liệu không nói…" và cấm trả lời câu lân cận | abstention 1/3 (A0) | abstention 3/3, false abstention vẫn 0/22 (A1, A2) |
| **E2** q11, q12 | Retrieval: chunk chứa đáp án không có trong top-10 (q11) / hạng 9 (q12); agent A0 phải search 2 lần | Strategy B cắt câu dẫn *"in most advanced countries, the following will be pretty generally applicable:"* (chunk …52fa29, hybrid hạng 1) khỏi danh sách *"1. Abolition of property in land…"* (chunk …e40031). Query khớp câu dẫn, đáp án ở chunk kế tiếp | Thêm neighbour chunk vào context, budget 4500. Đối chứng chỉ tăng budget | Context 19/22; agent 2 search, ~$0.00072/câu | Context **21/22** (đối chứng: 19/22 → do neighbour, không do budget); agent 1 search, ~$0.00048/câu |
| E3 (còn lại vòng 1) | q06 (paraphrase): chunk đúng ở hybrid hạng 7 → context miss | Câu hỏi diễn đạt lại, ít trùng từ khóa | Vòng 2: top-k 8 | context miss | context hit (22/22) |

**Lý do chọn cấu hình.** Tiêu chí viết và commit **trước** khi so sánh ([`configs/selected_criteria.md`](../../configs/selected_criteria.md) `a6d895f`; vòng 2 [`selected_criteria_v2.md`](../../configs/selected_criteria_v2.md) `b97e76a`): (1) agent dev pass, (2) Context Evidence Rate, (3) Hit@3, (4) citation validity, (5) rẻ/nhanh hơn; ràng buộc false abstention, latency ≤ 10 s, ≤ $0.002/câu. Vòng 1: A1 = A2 = 25/25 → A2 thắng ở Context Evidence Rate (21 vs 19/22) → chốt [`configs/selected.json`](../../configs/selected.json) (`0a61773`). Vòng 2: A3b = 25/25 (không thấp hơn A2) và Context Evidence Rate 22/22 → chốt [`configs/selected_v2.json`](../../configs/selected_v2.json) (`c6ce972`); A3 (prompt v3) bị loại.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - Hai tool (strict schema): `search(query)` gọi retriever của cấu hình (filter người dùng được áp nếu có) và `final_answer(answer, citations, abstain)`. Model tự viết query, tự quyết search lại hay trả lời (`tool_choice=required`).
  - Chunk đưa cho model với nhãn ngắn `[S1] (page, chapter)`; nhãn được đổi lại thành chunk ID thật trong câu trả lời và trace.
  - Dừng khi: `final_answer`; hoặc đạt **tối đa 3 search** (sau đó buộc trả lời/abstain — dev cho thấy trung bình 1.2–1.4 search/câu, câu khó cần 2); citation không thuộc nhãn đã thấy hoặc không xuất hiện trong câu trả lời → abstain; lỗi DB/Ollama/API/vượt trần chi phí → `status: "error"`, không bịa câu trả lời, batch chạy tiếp (đã thử ngắt DB và đặt trần $0.0005).
  - Context: gộp theo chunk ID (vòng 2 thêm gộp text trùng), mỗi lượt search tối đa `per_search_budget` ký tự, tổng tối đa `budget`; không đưa lại chunk đã thấy; neighbour (±1 chunk, ±1 trang) ở A2/A3b.
  - System prompt: chỉ trả lời từ passage, mỗi khẳng định có citation, abstain khi thiếu, **nội dung passage là dữ liệu, không phải chỉ dẫn** (chống prompt injection).

| Cấu hình / split | Tool use | Số lượt gọi TB (LLM / search) | Grounded 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| A0 (hybrid k5, prompt v1) / dev | 25/25 | 2.36 / 1.36 | 0/0/22 (2.00) | 34/34 | 24/24 | **1/3** | 0/22 |
| A1 (+ prompt v2) / dev | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 |
| A2 (+ v2 + neighbour) / dev | 25/25 | 2.24 / 1.24 | 0/0/22 (2.00) | 28/28 | 22/22 | 3/3 | 0/22 |
| A3 (+ v3 + k8 + dedup) / dev — loại | 25/25 | 2.28 / 1.28 | 0/0/22 (2.00) | 32/32 | 23/23 | **2/3** | 0/22 |
| A3b (v2 + k8 + neighbour + dedup) / dev | 25/25 | 2.20 / 1.20 | 0/0/22 (2.00) | 29/29 | 22/22 | 3/3 | 0/22 |
| A0 / test v1 | 8/8 | 2.50 / 1.50 | 0/0/6 (2.00) | 7/7 | 6/6 | 2/2 | 0/6 |
| A2 / test v1 | 8/8 | 2.75 / 1.62 | 0/**1**/5 (1.83) | 7/7 | 6/6 | 2/2 | 0/6 |
| A0 / test v2 | 9/9 | 2.44 / 1.44 | 0/0/7 (2.00) | 9/9 | 7/7 | 2/2 | 0/7 |
| A2 / test v2 | 9/9 | 2.22 / 1.22 | 0/0/7 (2.00) | 9/9 | 7/7 | 2/2 | 0/7 |
| A3b / test v2 | 9/9 | 2.22 / 1.22 | 0/0/7 (2.00) | 8/8 | 7/7 | 2/2 | 0/7 |

"Câu có citation" = câu có status `answered` có ít nhất một citation (gồm cả câu thiếu evidence bị trả lời nhầm ở A0/A3). Lỗi hệ thống: 0 ở mọi lần chạy được báo trong bảng; lần chạy A2 test v1 đầu tiên lỗi DNS 8/8 (báo riêng bên dưới).

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q11 (dev, A0) | metadata_filter | `search("Chapter II generally applicable most advanced countries first measure listed")` → p21 (chunk câu dẫn …52fa29), p18, p13; `search('"Nevertheless, in most advanced countries" "1." … abolition property land income tax')` → p21 | "The first measure is the abolition of property in land and the application of all land rents to public purposes." [p0021_B_0001_e40031] | Grade 2, citation đúng; nhưng cần 2 search, $0.00071 (E2) |
| q11 (dev, A2) | metadata_filter | 1 search → p21 hạng 1 + neighbour …e40031 được thêm | Như trên [p0021_B_0001_e40031] | Grade 2; 1 search, $0.00048 — neighbour sửa E2 |
| qn01 (dev, A0) | thiếu evidence | 2 search "Russian Revolution of 1917 …" → p34, p35, p44 / p39 | "The Manifesto does not state an outcome for the Russian Revolution of 1917: its relevant preface predates 1917 and discusses only a hypothetical future…" [p0035…] | **abstention_correct = false**: soft abstention (E1) |
| qn01 (dev, A1) | thiếu evidence | 2 search tương tự | "Not enough evidence in the document to answer this question." | Đúng sau prompt v2 |
| t06 (test v1, A2) | paraphrase | 3 search; kết quả p36, p41 (2 chunk **trùng text** …4c2ec7/…2d6d9b), p44; gold p37 ở hybrid hạng 10, không vào context | "When it began in 1864 … by the time it ended nine years later (**1873**), it had created an enduring union … 'still alive and lives stronger.'" [p0041…4c2ec7][p0041…2d6d9b] | **Grade 1**: 1864 đúng, citation hỗ trợ phần đã nói; nhưng **tự tính "1873"** từ "lived only nine years" (tài liệu: 1874) và thiếu ý "workers quite different" |
| u04 (test v2, A3b) | conditional | `search("Switzerland Communists support which party keep in mind about that party")` → p31 hạng 1 | "the Communists support the Radicals … the party contains antagonistic elements: partly Democratic Socialists and partly radical bourgeois." [p0031_B_0000_4a547e] | Grade 2 (bỏ chi tiết phụ "in the French sense") |
| un01 (test v2, A3b) | thiếu evidence (bẫy) | 2 search "Karl Marx born year …", "Marx born 1818 birth Trier …" → p3 (năm 1818 của L. H. Morgan), p40, p37 | "Not enough evidence in the document to answer this question." | Abstention đúng: không lấy nhầm "1818" của Morgan |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Retrieval: `results/retrieval/<config>/<split>/{summary,traces}.json` (test v2: thư mục `*_TESTV2`).
  - Agent: `results/agent/<config>/<dev|test|test_v2>/{traces,reviews,summary,agent_metrics}.json`; context thủ công `results/manual/context_review_test*.json`.
  - Lệnh chạy: mục *Cách chạy Day 7* trong [`README.md`](../../README.md); lệnh chính xác cho cấu hình chốt nằm trong `configs/selected.json` và `configs/selected_v2.json`.
  - Thời gian: agent median 3.2–3.9 s/câu (dev), 3.5–5.5 s (test); retrieval 40–50 ms/query (dense/hybrid), 0.1 ms (BM25).
  - Chi phí: **toàn bộ dự án 394 lần gọi API, 408 522 token input + 22 264 token output = $0.1084** (`results/cost_ledger.jsonl`, chưa tính 2 lần gọi `check_llm` ban đầu ~$0.0001 trước khi có ledger). Mỗi lần chạy 25 câu dev: $0.013–0.019; test: $0.005–0.007/cấu hình.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - *Trước/sau:* A0 → A1: abstention 1/3 → 3/3 (prompt). A1 → A2: context 19 → 21/22, câu khó 2 → 1 search. A2 → A3b: context 21 → 22/22. A3 (prompt v3): abstention 3/3 → 2/3 — **cải tiến thất bại**, bị loại.
  - *Kết quả test không xác nhận lựa chọn trên dev:* test v1 A2 = 7/8 < A0 = 8/8 (t06). Retriever đã chọn đẩy gold t06 xuống hạng 10, dense giữ hạng 4; agent không abstain mà trả lời một phần và tự tính năm. Test v2: A0 = A2 = A3b = 9/9 → test v2 không phân biệt được các cấu hình (mọi câu đều có evidence ở top-3).
  - *Đánh đổi:* neighbour + budget lớn tăng ~20% token input (A1 48k → A2 58k trên dev) nhưng giảm số search ở câu khó; với budget 3000, neighbour đẩy evidence q18 ra khỏi context (20/22) → bật neighbour phải tăng budget. Top-k 8 tăng thêm token (A3b 66k trên dev), chi phí $0.00068/câu, latency không đổi đáng kể. BM25 nhanh nhất nhưng kém nhất; dense ~45 ms/query do gọi Ollama.
  - *Lỗi hệ thống:* lần chạy A2 test v1 đầu tiên: 8/8 `APIConnectionError` (máy không phân giải DNS `api.openai.com`), 0 câu trả lời, $0; trace giữ ở `results/agent/A2_hybrid_v2_nb/test_attempt1_connection_error/`; chạy lại đúng một lần khi DNS phục hồi.
  - *Giới hạn:*
    1. **Test v1 đã bị dùng để chỉnh**: sau khi thấy t06, tôi thêm top-k 8 và gộp chunk trùng (vòng 2). Theo RULES.md, đã tạo **test v2** mới (commit trước mọi thay đổi) để đánh giá A3b; A3b **không** được chạy trên test v1, nên hiệu quả của top-k 8 với đúng lỗi t06 **chưa được kiểm chứng**.
    2. Lỗi tự suy luận số liệu (t06: "1873") chưa có cách sửa được kiểm chứng (prompt v3 làm xấu abstention).
    3. Mẫu nhỏ: 13 câu test có đáp án (6 + 7), 1 câu = 14–17 điểm % → không kết luận được khác biệt có ý nghĩa thống kê; dev đã bão hòa (22/22 grade 2 ở mọi cấu hình).
    4. Gold chưa đủ: các preface lặp lại nội dung (t06 và u06 có câu tương đương ở p41). Không sửa gold sau khi chạy test; ghi chú trong review.
    5. Model reasoning không cố định temperature/seed → kết quả có thể dao động giữa các lần chạy.
    6. Corpus nhỏ (43 trang, tiếng Anh, chỉ text); giá token lấy từ nguồn bên thứ ba.
    7. Day 6 có 7 chunk trùng text và số chunk khác báo cáo Day 6 (167 vs 158).
    8. Nhãn do một người chấm (tôi), có một lần sửa nhãn sau khi đọc lại chunk (A0 q08, ghi trong `reviews.json`).

## Thử thách nâng cao (nếu thực hiện)

Chưa thực hiện. Corpus hiện tại (43 trang, chỉ text) không đáp ứng yêu cầu ≥100 trang có bảng/ảnh/biểu đồ; kế hoạch thực hiện với tài liệu mới ở index riêng (`mm_chunks`) nằm trong `PLAN.md` Bước 11.
