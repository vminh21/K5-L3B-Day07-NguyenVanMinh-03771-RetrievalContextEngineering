# Báo cáo Day 7 — Agentic RAG trên *Manifesto of the Communist Party*

**MSSV:** 2A202603771 · **Họ tên:** Nguyễn Văn Minh

Báo cáo này trình bày quá trình xây một agent RAG trả lời câu hỏi về *Manifesto of the Communist Party*, dùng lại vector store của Day 6. Mọi con số đều lấy từ các file kết quả trong `results/` (`summary.json`, `traces.json`, `reviews.json`, `agent_metrics.json`) và sổ chi phí `results/cost_ledger.jsonl`. Bảng chi tiết hơn nằm ở [`dev_experiments.md`](../../results/dev_experiments.md), [`test_results.md`](../../results/test_results.md), [`test_v2_results.md`](../../results/test_v2_results.md) và [`test_v3_results.md`](../../results/test_v3_results.md). Cách chạy lại nằm ở mục [Cách chạy](#cách-chạy) cuối báo cáo. Có một demo Streamlit (`streamlit run demo/app.py`).

**Tóm tắt.** Cấu hình được chọn là **A2**: hybrid RRF (dense + BM25), thêm chunk liền kề (neighbour), lấy top-5, context tối đa 4500 ký tự mỗi lượt search, và prompt v2 với luật từ chối chặt. Trên bộ test độc lập lớn nhất (test v3, 26 câu), A2 đạt **26/26**. Tuy vậy, baseline dense cũng đạt 26/26, và ở bước retrieval dense còn nhỉnh hơn. Hai cải tiến có tác dụng rõ là prompt v2 (tỉ lệ từ chối đúng 1/3 → 3/3) và neighbour chunk (Context Evidence Rate trên dev 19 → 22/22). Hai lỗi vẫn chưa sửa được: model tự tính năm ở câu t06, và neighbour có thể đẩy kết quả hạng 3–5 ra khỏi context. Toàn bộ dự án tốn **$0.2226** trên trần $1.

## Dữ liệu và benchmark

**Nguồn, quyền sử dụng, số trang và số chunk.** Tài liệu là *Manifesto of the Communist Party* của Marx và Engels, bản dịch tiếng Anh của Samuel Moore (1888), lấy từ bản PDF 2005 của Marxists Internet Archive (https://www.marxists.org/archive/marx/works/1848/communist-manifesto/). Tài liệu thuộc **Public Domain** (chi tiết ở [`data/day7/SOURCE.md`](../../data/day7/SOURCE.md)). File có 44 trang; bỏ trang bìa còn 43 trang nội dung (trang 2–44). Tôi dùng lại index của Day 6 theo strategy B: chia theo đoạn văn, tối đa 1000 ký tự, không overlap, được **167 chunk**. Có hai điểm cần lưu ý. Thứ nhất, báo cáo Day 6 ghi 158 chunk nhưng DB hiện có 167; Day 7 dùng đúng nội dung trong DB. Thứ hai, có 7 đoạn bị lưu hai lần (text giống hệt, ID khác).

**Vector store, embedding model, phiên bản và số chiều.** Vector store là PostgreSQL 16 với pgvector **0.8.7** (chạy Docker, cổng 55433, bảng `chunks` của Day 6), dùng khoảng cách cosine. Embedding là `embeddinggemma` chạy qua Ollama, **768 chiều**, giữ nguyên prefix query và document của Day 6. BM25 đọc file `data/day7/chunks.json`, được export từ chính DB đó; tôi đã kiểm tra hai bên có cùng tập chunk ID. Ở vòng 3 tôi có thử thêm reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` chạy local, nhưng cuối cùng không dùng.

**Agent model, cách chạy và phân chia dev/test.** Agent dùng API **`gpt-5.6-luna`** của OpenAI qua Responses API, `reasoning.effort=low`. Chi phí được tính theo giá $0.20 / $1.20 cho mỗi 1 triệu token input / output (giá lấy từ nguồn bên thứ ba). Mọi lần gọi API đều được ghi vào `results/cost_ledger.jsonl`, và có trần cứng `MAX_COST_USD=1.0`: chạm trần thì agent dừng và báo lỗi, không bịa câu trả lời.

Benchmark được chia thành nhiều split. Mỗi bộ test được commit trước khi dùng; khi một bộ test đã bị xem để chỉnh, tôi tạo bộ mới thay vì dùng lại.

| Split | Có đáp án | Thiếu evidence | Commit | Vai trò |
|---|---:|---:|---|---|
| dev | 22 | 3 | `e70e0a3` | Chỉnh và chọn cấu hình (22 câu của Day 6) |
| dev_hard | 8 | 2 | `e6e0513` | Chỉnh ở vòng 3, vì dev cũ đã đạt 22/22 ở mọi cấu hình |
| test v1 | 6 | 2 | `e70e0a3` | Đánh giá vòng 1; **không còn độc lập** vì đã dùng để chẩn đoán t06 |
| test v2 | 7 | 2 | `6fa2c93` | Đánh giá vòng 2 |
| **test v3** | **20** | **6** | `e6e0513` | Đánh giá vòng 3, chạy đúng một lần |
| **Tổng** | **63** | **15** | | |

Test v3 được làm lớn hơn và khó hơn hẳn các bộ trước, và không dùng chung chunk evidence nào với các split khác. Nó gồm 5 câu diễn đạt lại (ít trùng từ khóa), 6 câu hỏi số/ngày (vài câu dễ dụ model tự tính), 3 câu multi-hop phải ghép hai đoạn, 4 câu có điều kiện, 1 câu hỏi mục danh sách bị chunk cắt đôi, và 1 câu về chú thích của Engels. Sáu câu thiếu evidence đều là **câu bẫy gần đúng**. Ví dụ, tài liệu có nhắc ấn bản 1888 nhưng không ghi số bản in; tài liệu có câu "bị kết án 3 đến 6 năm" nhưng đó không phải án của Marx.

**Cách xác định câu có/thiếu evidence và tiêu chí chấm.** Với câu có đáp án, gold là một trích dẫn nguyên văn nằm trọn trong một chunk đúng trang (kiểm tra bằng hàm `validate()` của starter). Nếu nội dung lặp lại ở nhiều lời tựa, các đoạn lặp được ghi thành gold thay thế. Với câu thiếu evidence, trường `absence_reason` ghi lại cách tôi đã grep toàn bộ 167 chunk để chắc chắn tài liệu không có thông tin đó. Agent chỉ nhận `id`, `question` và `filter`, không bao giờ nhận gold.

Tôi chấm tay từng câu. Câu trả lời được 0 điểm nếu sai hoặc thiếu evidence, 1 nếu đúng một phần, 2 nếu đúng và đủ; câu multi-hop phải trả lời đủ mọi phần mới được 2. Mỗi citation được đọc lại để xem đoạn đó có thực sự hỗ trợ câu trả lời không. Với câu thiếu evidence, tôi kiểm tra agent có thực sự từ chối hay không, hay vẫn đưa ra khẳng định.

Sau khi chạy test, tôi phát hiện t06 và u06 còn một câu tương đương ở trang 41, do các lời tựa lặp lại nội dung. Hai câu này được bổ sung làm gold thay thế ([`gold_correction.md`](../../results/gold_correction.md)). Retrieval được chấm lại từ trace đã lưu, không chạy lại, và nhãn chấm agent không thay đổi.

## Retrieval và thử nghiệm

Tất cả cấu hình được đo trên cùng corpus, cùng index và cùng bộ nhãn. Context budget đo bằng **ký tự** (tính cả header của mỗi chunk). Hit@1 và Evidence Hit@3 tính theo danh sách xếp hạng của **câu hỏi gốc**, chưa qua bước agent viết lại query. Context Evidence Rate (CtxEv) đo xem evidence có nằm trong context cuối cùng gửi cho model hay không. Với câu multi-hop, Hit@k chỉ cần có một evidence bắt buộc, còn CtxEv đòi đủ **mọi nhóm** evidence. Retrieval chạy local nên chi phí bằng $0.

Ở vòng 3 tôi phát hiện một lỗi trong cách đo CtxEv: code bỏ sót trang của các chunk neighbour, nên câu q06 bị tính là trượt dù evidence có trong context. Mọi bảng dưới đây dùng số **đã sửa** (chi tiết ở [`metric_bugfix.md`](../../results/metric_bugfix.md)).

Bảng đầu tiên so sánh ba phương pháp bắt buộc và các cải tiến trên dev:

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
| Continuation-first — **loại** | A2 + gộp trùng; neighbour của chunk bị cắt được ưu tiên | Budget bị neighbour của hit hạng 1 chiếm | 18/22 | 19/22 | 22/22 (100%) | 37.9 ms |

Dense và BM25 sai ở những câu khác nhau, nên gộp chúng bằng RRF cho kết quả tốt hơn cả hai: Hit@1 tăng từ 15 lên 18/22. Hybrid vì vậy vừa là phương pháp thứ ba, vừa là cải tiến đầu tiên so với dense. Dòng đối chứng cho thấy chỉ tăng budget lên 4500 mà không thêm neighbour thì CtxEv vẫn là 19/22. Nghĩa là mức tăng lên 22/22 đến từ neighbour, không phải từ budget lớn hơn. Hai thử nghiệm của vòng 3 (rerank và continuation-first) đều không giúp được gì trên dev.

Vì dev cũ đã gần bão hòa, tôi viết thêm 10 câu dev khó (dev_hard) để phân biệt các cấu hình ở vòng 3:

| Cấu hình | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian |
|---|---|---|---|---|
| Dense | 3/8 (37.5%) | 7/8 (87.5%) | 6/8 (75.0%) | 41.3 ms |
| BM25 | 7/8 (87.5%) | 7/8 (87.5%) | 6/8 (75.0%) | 0.2 ms |
| Hybrid | 7/8 (87.5%) | 8/8 (100%) | 7/8 (87.5%) | 38.9 ms |
| **A2** | 7/8 (87.5%) | 8/8 (100%) | **8/8 (100%)** | 48.3 ms |
| Rerank (A4r) | 7/8 (87.5%) | 7/8 (87.5%) | **6/8 (75.0%)** | 117.7 ms |
| Continuation-first | 7/8 (87.5%) | 8/8 (100%) | **7/8 (87.5%)** (h04) | 37.6 ms |

Trên dev_hard, A2 vẫn là cấu hình duy nhất đưa đủ evidence vào context cho cả 8 câu. Rerank làm mất 2 câu, còn continuation-first làm mất câu multi-hop h04.

Sau khi chốt cấu hình ở mỗi vòng, tôi mới chạy retrieval trên bộ test tương ứng:

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | CtxEv | Thời gian |
|---|---|---|---|---|---|
| Baseline (dense) | test v1 | 3/6 (50.0%) | 5/6 (83.3%) | 6/6 (100%) | 49.6 ms |
| A2 (chọn vòng 1) | test v1 | 4/6 (66.7%) | 5/6 (83.3%) | 5/6 (83.3%), trượt t06 | 45.7 ms |
| Baseline (dense) | test v2 | 6/7 (85.7%) | 7/7 (100%) | 7/7 (100%) | 45.1 ms |
| A2 | test v2 | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 41.9 ms |
| A3b (chọn vòng 2) | test v2 | 7/7 (100%) | 7/7 (100%) | 7/7 (100%) | 50.7 ms |
| **Baseline (dense)** | **test v3** | **18/20 (90.0%)** | **20/20 (100%)** | **19/20 (95.0%)**, trượt v16 | 42.4 ms |
| **A2 (chọn vòng 3)** | **test v3** | 16/20 (80.0%) | 19/20 (95.0%) | 18/20 (90.0%), trượt v01, v16 | 40.2 ms |
| A2 + gộp trùng (retriever của A4) | test v3 | 16/20 (80.0%) | 19/20 (95.0%) | 18/20 (90.0%) | 44.0 ms |

Kết quả test không xác nhận hoàn toàn những gì thấy trên dev. Trên test v3, **dense tốt hơn hybrid**. Ở câu diễn đạt lại v01, hybrid xếp đoạn đúng ở hạng 7, trong khi dense xếp hạng 1. Câu multi-hop v16 thì cả hai đều không đưa đủ hai đoạn vào context. Dù vậy, ở mức agent cả hai đều trả lời đúng 20/20, vì agent tự viết lại query và search thêm khi cần.

**Hai lỗi dev và các lỗi phát hiện sau.** Bảng dưới tóm tắt các lỗi chính, nguyên nhân và cách tôi đã thử sửa.

| Lỗi | Hiện tượng | Nguyên nhân | Thay đổi | Trước | Sau |
|---|---|---|---|---|---|
| **E1** qn01, qn03 (dev) | Câu thiếu evidence vẫn bị trả lời kiểu "The Manifesto does not state…" kèm citation | Prompt v1 chỉ nói "từ chối nếu thiếu evidence" | Prompt v2: từ chối khi passage không trả lời **đúng câu hỏi** | Từ chối đúng 1/3 | **3/3**, không từ chối nhầm câu nào |
| **E2** q11, q12 (dev) | Đáp án nằm ở chunk ngay sau câu dẫn "…the following will be pretty generally applicable:" | Strategy B tách câu dẫn khỏi danh sách | Thêm neighbour chunk, budget 4500; đối chứng chỉ tăng budget | CtxEv 19/22, 2 search/câu | **22/22** (đối chứng 19/22), 1 search |
| **E4** t06 (test v1) | Model **tự tính "1873"**, trong khi tài liệu ghi 1874 | Model suy luận số học trên passage | Bộ kiểm tra số `src/numcheck.py` | Prompt v3 thất bại (vòng 2) | Bắt được "1873" khi chạy offline, chặn "90%" ở h07; **nhưng** báo nhầm nhiều |
| **E5** q12 (A4, dev lần 1), v07 (A4, test v3) | Từ chối nhầm dù đoạn đúng được retrieve ở hạng 3–5 | Neighbour của kết quả hạng cao chiếm hết budget 4500 | Continuation-first | — | Sửa được q12 nhưng làm hỏng h04, nên bị loại; **chưa sửa** |

E1 và E2 là hai lỗi tìm thấy trên dev và đã sửa được. E4 xuất hiện ở test v1, nên mọi cách sửa đều phải kiểm chứng trên dev và trên một bộ test mới. E5 là lỗi do chính cải tiến neighbour gây ra. Nó chỉ xảy ra khi model viết query khiến đoạn đúng rơi xuống hạng 3–5, nên lúc có lúc không giữa các lần chạy.

Để biết bộ kiểm tra số có đáng tin không, tôi chạy nó offline trên toàn bộ **296 câu trả lời đã lưu**, không gọi thêm API ([`numcheck_offline_replay.json`](../../results/manual/numcheck_offline_replay.json)):

| Trường hợp bị báo | Số | Đúng / nhầm | Lý do |
|---|---|---|---|
| A2 / test v1 / t06 | 1873 | **Đúng** | Tài liệu ghi 1874 |
| A2 / test v1 / t06 | 1 | Nhầm | Đại từ "one" bị đọc thành số |
| u07 (test v2, 3 cấu hình) | 10 | Nhầm | Tài liệu ghi "tenfold", câu trả lời ghi "ten times" |
| A0 / test v3 / v09 | 1860 | Nhầm | Tài liệu ghi "'sixties", câu trả lời ghi "1860s" |

Bộ kiểm tra báo đúng 1 lần và báo nhầm 4 lần. Nếu đưa vào sử dụng, nó có thể buộc model sửa hoặc từ chối cả những câu đang đúng. Tôi không chỉnh bộ kiểm tra sau khi thấy kết quả này, vì làm vậy chính là chỉnh theo dữ liệu test.

**Lý do chọn cấu hình.** Ở cả ba vòng, tiêu chí chọn đều được commit trước khi đo; thứ tự ưu tiên là tỉ lệ đạt của agent, rồi CtxEv, rồi Hit@3, citation, cuối cùng là chi phí và tốc độ.

| Vòng | Tiêu chí | Ứng viên và kết quả | Chọn | Commit |
|---|---|---|---|---|
| 1 | [`selected_criteria.md`](../../configs/selected_criteria.md) | A1 = A2 = 25/25; CtxEv của A2 cao hơn | **A2** | `2f28739` |
| 2 | [`selected_criteria_v2.md`](../../configs/selected_criteria_v2.md) | A3b 25/25, CtxEv 22/22; A3 (prompt v3) bị loại vì từ chối đúng chỉ 2/3 | A3b | `af9cdc7` |
| 3 | [`selected_criteria_v3.md`](../../configs/selected_criteria_v3.md): giữ top-k = 5 | dev_hard: A2 = A4 = A4r = 10/10; dev chạy 2 lần: A2 **50/50**, A4 49/50 | **A2** | `7b8354e` |

Lựa chọn ở vòng 2 hóa ra dựa trên số đo sai. Khi đó tôi chọn A3b vì tưởng top-k 8 nâng CtxEv từ 21 lên 22/22, nhưng sau khi sửa lỗi đo thì A2 cũng đã đạt 22/22, nên lẽ ra phải chọn A2 vì rẻ hơn. Ở vòng 3, sau lần chạy dev đầu tiên A2 được 25/25 và A4 được 24/25. Chênh lệch chỉ một câu, và câu đó trượt vì query model tự viết chứ không vì thành phần mới của A4. Vì vậy tôi viết thêm một phụ lục vào tiêu chí (commit `9a22c64`, **trước** lần đo thứ hai): chạy dev thêm một lần cho cả hai và quyết định theo tổng hai lần. A2 thắng 50/50 so với 49/50. A4 vẫn được chạy trên test v3, nhưng được khai báo trước là ablation, không dùng để chọn.

## Agent và đánh giá

**Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi.** Agent có hai tool với schema chặt: `search(query)` để tìm trong tài liệu, và `final_answer(answer, citations, abstain)` để trả lời hoặc từ chối. Model tự viết query và tự quyết định search tiếp hay trả lời. Các chunk được đưa cho model với nhãn ngắn `[S1]`, `[S2]`… kèm trang và chương. Trong câu trả lời cuối và trong trace, các nhãn này được đổi lại thành chunk ID thật, nên có thể kiểm tra từng citation.

Agent được search tối đa **3 lần**; thực tế trung bình chỉ 1.2–1.4 lần search và 2.2–2.5 lần gọi LLM mỗi câu. Agent dừng khi gọi `final_answer`, hoặc khi hết lượt search (lúc đó buộc phải trả lời hoặc từ chối). Nếu citation trỏ tới nhãn không tồn tại, câu trả lời bị đổi thành từ chối. Khi gặp lỗi DB, Ollama, API hoặc chạm trần chi phí, câu đó được ghi `status: "error"` và cả lượt chạy vẫn tiếp tục. Agent không bao giờ bịa câu trả lời trong trường hợp lỗi.

Context được gộp theo chunk ID; A4 còn gộp các chunk có text giống hệt. Mỗi lượt search có budget riêng, cộng thêm một budget tổng. Chunk đã đưa cho model sẽ không được đưa lại, kể cả dưới dạng neighbour. Riêng A4 có thêm bộ kiểm tra số: mọi con số trong câu trả lời phải xuất hiện trong passage được cite; nếu không, model được sửa một lần, vẫn sai thì từ chối. System prompt nói rõ nội dung passage chỉ là dữ liệu, không phải chỉ dẫn, để chống prompt injection.

Kết quả chấm tay của tất cả các lần chạy agent:

| Cấu hình / split | Tool use | Số lượt gọi TB (LLM / search) | Grounded 0/1/2 (TB) | Citation hợp lệ | Câu có citation | Từ chối đúng | Từ chối nhầm |
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

Mọi câu đều có gọi tool search, và mọi citation đều được xác nhận là hỗ trợ câu trả lời. Khác biệt nằm ở hai chỗ. Thứ nhất là khả năng từ chối: prompt v1 (A0 trên dev) chỉ từ chối đúng 1/3 câu thiếu evidence, prompt v3 làm tụt xuống 2/3. Thứ hai là vài câu trả lời sai hoặc từ chối nhầm lẻ tẻ: t06 của A2 ở test v1, và q12, v07 của A4. Trên test v3, cả A0 lẫn A2 đều không sai câu nào, kể cả 6 câu bẫy. Không có lỗi hệ thống nào trong các lần chạy ở bảng. Riêng lần chạy A2 trên test v1 đầu tiên bị lỗi DNS cả 8 câu (`APIConnectionError`, không tốn tiền); trace được giữ ở `results/agent/A2_hybrid_v2_nb/test_attempt1_connection_error/` và tôi chạy lại đúng một lần.

Một số câu tiêu biểu, gồm cả câu đúng và câu sai:

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q11 (dev, A2) | metadata_filter | 1 search → câu dẫn ở p21 hạng 1, kèm neighbour …e40031 | "The first measure is the abolition of property in land…" [p0021…e40031] | Grade 2; neighbour sửa E2 (A0 cần 2 search) |
| qn01 (dev, A0 → A1) | thiếu evidence | 2 search "Russian Revolution of 1917…" | A0: "The Manifesto does not state an outcome for … 1917…" [p0035…] → A1: từ chối | E1, sửa bằng prompt v2 |
| t06 (test v1, A2) | paraphrase | 3 search; đoạn đúng ở p37 bị hybrid xếp hạng 10, không vào context | "…ended nine years later (**1873**)…" [p0041…4c2ec7][p0041…2d6d9b] | **Grade 1**: tự tính năm (E4) |
| t06 (chẩn đoán, A4, **không độc lập**) | paraphrase | 1 search "…years 1864 1872" → đoạn đúng p37 …46eb1b vào context | "It began in **1864** and broke up in **1874**…" [p0037…46eb1b][p0037…b9bd5a] | Grade 2, nhưng bộ kiểm tra số **không kích hoạt**; đúng là nhờ query khác |
| h07 (dev_hard, A4) | numeric | 1 search → p15 | Bản nháp ghi "90%" bị bộ kiểm tra từ chối → model sửa thành "nine-tenths of the population" [p0015…] | Grade 2; bộ kiểm tra số hoạt động đúng |
| v07 (test v3, A4) | numeric | 3 search; đoạn đúng …f4daba ở hạng 3 và 5 nhưng không vào context | "Not enough evidence…" | **Từ chối nhầm** (E5); chạy lại cho thấy không phải do gộp trùng hay bộ kiểm tra số |
| v10 (test v3, A2) | multi-hop | 1 search → p35, p38 | "…'solely and exclusively to Marx' … what Darwin's theory has done for biology" [p0035…e4cf4c][p0038…745803] | Grade 2, đủ cả hai nhóm evidence |
| w06 (test v3, cả 3 cấu hình) | thiếu evidence (bẫy) | 2 search về án của Marx → p36 "seven prisoners … three to six years" | "Not enough evidence…" | Từ chối đúng: không gán án 3–6 năm cho Marx |

Hai câu t06 cho thấy vì sao tôi không coi t06 là đã sửa. Lần chạy chẩn đoán trả lời đúng, nhưng là nhờ model viết một query khác kéo được đoạn đúng vào context; bộ kiểm tra số không hề tham gia. Hơn nữa, test v1 đã bị xem từ trước nên kết quả này không độc lập.

**Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí.** Trace retrieval nằm ở `results/retrieval/<config>/<split>/`; kết quả test v2, test v3 và dev_hard nằm ở các thư mục có hậu tố `_TESTV2`, `_TESTV3`, `_DEVHARD`. Trace, nhãn chấm tay và metric của agent nằm ở `results/agent/<config>/<split>/` (các file `traces`, `reviews`, `summary`, `agent_metrics`). Phần chấm context thủ công nằm ở `results/manual/context_review_test*.json`. Tham số của cấu hình đã chốt nằm ở [`configs/selected_v3.json`](../../configs/selected_v3.json), còn lệnh chạy ở mục [Cách chạy](#cách-chạy).

| Lần chạy | Chi phí | Median latency | Token input |
|---|---|---|---|
| Agent dev, 25 câu (mỗi lần) | $0.014–0.016 | 3.5–4.9 s/câu | 53–60k |
| Agent dev_hard, 10 câu | $0.006–0.007 | 4.1–4.4 s/câu | 22–27k |
| A0 / test v3 | $0.0138 | 4.4 s/câu | 49k |
| A2 / test v3 | $0.0150 | 3.6 s/câu | 57k |
| A4 / test v3 | $0.0188 | 3.9 s/câu | 74k |
| Retrieval dense / hybrid / BM25 / rerank | $0 | 40–50 / 37–48 / 0.1 / 107–118 ms | — |
| **Toàn dự án (benchmark)** | **$0.2226** (816 lần gọi; 839 999 token input + 45 493 token output) | | |
| Demo (kiểm tra app và dùng thử) | ghi riêng trong `demo/demo_cost_ledger.jsonl` | 3.9–12.6 s/câu | — |

**Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn.** Bảng dưới tóm tắt số phận của từng thay đổi đã thử:

| Thay đổi | Trước → sau | Kết luận |
|---|---|---|
| Prompt v1 → v2 (A0 → A1) | Từ chối đúng 1/3 → 3/3 | Giữ |
| Thêm neighbour (A1 → A2) | CtxEv dev 19 → 22/22; câu khó cần 2 → 1 search | Giữ |
| Prompt v3 (A3) | Từ chối đúng 3/3 → 2/3 | Loại |
| Top-k 8 (A3b) | Không hơn A2 sau khi sửa lỗi đo | Không cần |
| Rerank (A4r) | CtxEv dev 22 → 19, dev_hard 8 → 6 | Loại |
| Continuation-first | CtxEv dev_hard 8 → 7 | Loại |
| Bộ kiểm tra số + gộp trùng (A4) | Dev 49/50 so với A2 50/50; test v3 25/26 so với 26/26 | Không chọn |

Mọi cải tiến đều có giá. Neighbour cùng budget 4500 làm token input tăng khoảng 16% (trên test v3: A0 49k, A2 57k), bù lại câu khó cần ít lượt search hơn. A4 tốn thêm khoảng 28% token so với A2 (74k), do có thêm lượt sửa và lượt search. Rerank không tốn tiền nhưng làm retrieval chậm khoảng 2.5 lần (~110 ms mỗi query). Quan trọng nhất, neighbour vừa sửa được lỗi chunk bị cắt (E2) vừa sinh ra lỗi E5: nó có thể đẩy kết quả hạng 3–5 ra khỏi budget.

Báo cáo này còn một số giới hạn cần nói rõ:

1. **Test v3 không phân biệt được baseline với cấu hình chọn.** A0 và A2 cùng đạt 26/26, và ở bước retrieval dense còn tốt hơn. Kết luận trung thực là phần lớn độ chính xác đến từ việc agent tự viết lại query và từ prompt v2; lợi ích của hybrid + neighbour chỉ thấy rõ trên dev.
2. **Lựa chọn ở vòng 2 (A3b) dựa trên một lỗi đo**, như đã giải thích ở phần chọn cấu hình.
3. **t06 chưa được sửa một cách kiểm chứng được** khi giữ top-k = 5. Rerank đưa được đoạn đúng lên top-5 nhưng làm hỏng dev. Bộ kiểm tra số báo nhầm 4 trên 5 lần. Lần chạy chẩn đoán đúng là nhờ query. Và test v1 không còn độc lập.
4. **E5 chưa sửa.** Hướng tiếp theo là luôn đưa mọi kết quả search vào trước rồi mới tới neighbour, nhưng chừa chỗ cho neighbour chứa evidence của câu multi-hop. Bộ kiểm tra số cần hiểu được "-fold", "'sixties" và đại từ "one". Cả hai thay đổi phải được kiểm chứng trên một bộ test **mới**, vì test v3 đã bị xem.
5. **Kết quả dao động giữa các lần chạy** vì model không có seed. Ví dụ, q12 lúc đúng lúc sai với cùng một cấu hình. Trên test v3, một câu tương đương 5 điểm phần trăm, nên chênh lệch một câu không có ý nghĩa thống kê.
6. **Gold được bổ sung sau khi chạy** cho t06 và u06; ở v09, A0 dùng một đoạn thay thế ở trang 34 và vẫn được chấm 2. Việc bổ sung không làm thay đổi nhãn agent nào.
7. **Phạm vi hẹp:** corpus nhỏ, chỉ có text tiếng Anh; giá token lấy từ nguồn bên thứ ba; Day 6 có 7 chunk trùng; toàn bộ nhãn do một người chấm.

## Demo (Streamlit)

Để người xem tự kiểm tra agent, tôi làm một demo Streamlit trong `demo/app.py`. Chạy `streamlit run demo/app.py` rồi mở http://localhost:8501. Demo có ba tab:

| Tab | Chức năng | Cần gì | Chi phí |
|---|---|---|---|
| 💬 Chat với agent | Giao diện **chat**: mỗi câu trả lời kèm danh sách gọn các **tool agent đã gọi** (`search("…")` → số chunk, trang; `final_answer(citations=…)`) và dòng thông tin (retriever, top-k, prompt, thời gian, chi phí). Khung bên phải cho **chọn cách retrieval** (Hybrid + neighbour, Dense, BM25, Hybrid, Rerank), **số chunk top-k 3–5 (mặc định 3)**, prompt, filter, kiểm tra số, và **hiện các chunk retriever đã chọn** (⭐ = được cite; hạng, score); chunk liền kề do neighbour thêm vào được gom riêng một dòng | Postgres Day 6, Ollama, `OPENAI_API_KEY` | ~$0.0005–0.002 / câu |
| 🔎 So sánh retrieval | Top-5 của dense, BM25 và hybrid đặt cạnh nhau; đánh dấu chunk cả ba cùng tìm thấy | Postgres Day 6, Ollama | $0 |
| 📊 So sánh cấu hình trên benchmark | So sánh mọi cấu hình (A0–A4r) trên mọi bộ câu hỏi, kèm biểu đồ % đạt và chi phí; so sánh các phương pháp retrieval (Hit@1, Context Evidence Rate); bảng đối chiếu từng câu × từng cấu hình và tool call của từng câu | Không cần, đọc từ `results/` | $0 |

Mọi lựa chọn trong demo dùng **cùng LLM** `gpt-5.6-luna`; chúng chỉ khác nhau ở retriever, prompt và cách đưa context vào model. Vì vậy demo so sánh **cấu hình**, không so sánh các LLM khác nhau. Mỗi câu hỏi được agent xử lý độc lập (không dùng lịch sử chat làm ngữ cảnh), giống cách chạy benchmark.

Chi phí của demo được ghi vào sổ riêng `demo/demo_cost_ledger.jsonl`, để không làm sai số liệu benchmark. Tuy vậy, trần `MAX_COST_USD` vẫn tính trên tổng chi phí benchmark cộng demo. Tôi đã kiểm tra demo bằng công cụ test của Streamlit (AppTest): mọi tab và mọi bộ câu hỏi đều chạy không lỗi. Khi thử chat, câu "What does Chapter I say the bourgeoisie produces above all?" với Hybrid + neighbour được trả lời đúng ("its own grave-diggers", trang 12, 4.2 s, $0.00046). Sau khi đổi sang BM25, câu bẫy về án tù của Marx được từ chối đúng, và khung chunk hiện 4 đoạn BM25 tìm được (trang 36, 40, 34, 35).

## Cách chạy

Cần chạy trước Postgres và Ollama của Day 6, sau đó cài môi trường và tạo file `.env` chứa mật khẩu DB, `OPENAI_API_KEY` và `MAX_COST_USD`. File `.env` không được commit.

| Bước | Lệnh |
|---|---|
| Hạ tầng Day 6 | `cd ../K5-L3B-Day06-NguyenVanMinh-2A202603771-DataIngestion/starter && docker compose -p day6_student_starter up -d --wait`; `ollama list` (cần `embeddinggemma`) |
| Môi trường | `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| Kiểm tra | `.venv/bin/python -m unittest discover -s tests -v` · `python -m src.smoke_test` · `python -m src.check_llm` |
| Dữ liệu, benchmark | `python -m src.export_day6 --strategy B` · `python -m src.build_benchmark` · `--test-v2` · `--round3` |
| Retrieval | `python -m src.eval_retrieval --method {dense,bm25,hybrid,rerank} --split dev [--budget 4500 --neighbors] [--questions data/day7/test_v3/questions.json --split test]` |
| Agent (A2 đã chọn) | `python -m src.run_agent --split test --cases data/day7/test_v3/cases.json --out-split test_v3 --method hybrid --prompt v2 --neighbors --per-search-budget 4500 --budget 9000 --config A2_hybrid_v2_nb` |
| Baseline A0 | `python -m src.run_agent … --method dense --prompt v1 --per-search-budget 3000 --budget 6000 --config A0_dense_baseline` |
| Tổng hợp nhãn | `python starter/agent_metrics.py --cases <cases.json> --traces <traces.json> --reviews <reviews.json> --split test --output <agent_metrics.json>` |
| Chấm lại retrieval từ trace | `python -m src.rescore_retrieval results/retrieval/<cfg>/<split> <questions.json>` |
| Demo | `.venv/bin/streamlit run demo/app.py` |

Tham số đầy đủ của từng cấu hình nằm trong `configs/selected.json`, `selected_v2.json` và `selected_v3.json`.

Ghi chú về commit hash: lịch sử git đã được viết lại một lần, để bỏ dòng co-author và trả `README.md` về đúng bản của ban tổ chức. Nội dung, thứ tự và thời gian commit giữ nguyên; các hash trong báo cáo là hash mới.

## Thử thách nâng cao (nếu thực hiện)

Tôi chưa làm phần này. Corpus hiện tại chỉ có 43 trang text, không đáp ứng yêu cầu tài liệu từ 100 trang trở lên có bảng, ảnh và biểu đồ. Kế hoạch thực hiện (dùng một index riêng `mm_chunks`) nằm ở Bước 11 trong `PLAN.md`.
