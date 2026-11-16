# Thử nghiệm trên DEV (chọn cấu hình) — 2026-11-16

## Retrieval (22 câu có đáp án, query gốc, top-5 vào context)

| Cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | MRR@10 | Context TB (ký tự) | Median ms | Chi phí |
|---|---|---|---|---|---|---|---|
| M1 Dense (Day 6 pgvector) | 15/22 (68.2%) | 18/22 (81.8%) | 18/22 (81.8%) | 0.767 | 2704 | 46.6 | $0 |
| M2 BM25 | 14/22 (63.6%) | 17/22 (77.3%) | 17/22 (77.3%) | 0.71 | 2642 | 0.1 | $0 |
| M3 Hybrid RRF | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 0.852 | 2722 | 40.8 | $0 |
| M3 + budget 4500 (control) | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 0.852 | 3953 | 39.3 | $0 |
| C1a Hybrid + neighbours, 3000 | 18/22 (81.8%) | 19/22 (86.4%) | 20/22 (90.9%) | 0.852 | 2851 | 43.3 | $0 |
| C1b Hybrid + neighbours, 4500 | 18/22 (81.8%) | 19/22 (86.4%) | 21/22 (95.5%) | 0.852 | 4297 | 39.9 | $0 |

## Agent (gpt-5.6-luna, reasoning effort low, 25 câu dev = 22 có đáp án + 3 thiếu evidence; chấm thủ công trong `reviews.json`)

| Cấu hình | Thay đổi | Pass (grade 2 + abstain đúng) | Grounded grade 2 | Abstention đúng | False abstention | Citation hỗ trợ | Search TB | Median s | Token in/out | Chi phí (tổng / câu) |
|---|---|---|---|---|---|---|---|---|---|---|
| A0_hybrid_k5_s3 | baseline: hybrid, ≤3 search, prompt v1, 3000/6000 ký tự | 23/25 | 22/22 | 1/3 | 0/22 | 34/34 | 1.36 | 3.9 | 48727/3535 | $0.0140 / $0.00056 |
| A1_hybrid_v2 | + prompt v2 (luật abstain chặt) | 25/25 | 22/22 | 3/3 | 0/22 | 28/28 | 1.28 | 3.5 | 48069/3057 | $0.0133 / $0.00053 |
| A2_hybrid_v2_nb | + prompt v2 + neighbours, 4500/9000 ký tự | 25/25 | 22/22 | 3/3 | 0/22 | 28/28 | 1.24 | 3.6 | 57600/3249 | $0.0154 / $0.00062 |

## Phân tích lỗi dev (≥2)

| ID | Hiện tượng | Nguyên nhân (giả thuyết) | Thay đổi | Trước | Sau |
|---|---|---|---|---|---|
| E1: qn01, qn03 | Câu thiếu evidence nhưng agent trả `answered`: "The Manifesto does not state…" rồi trả lời câu hỏi lân cận (preface 1882 về Nga; lương = chi phí sinh tồn) kèm citation | Prompt v1 chỉ nói "abstain nếu thiếu evidence"; model coi việc *nói* là thiếu + trả lời phần liên quan là hữu ích, không đặt `abstain=true` | Prompt v2: chỉ đổi luật 4 — abstain khi passage không trả lời **đúng câu hỏi**, cấm kiểu "tài liệu không nói…" và cấm trả lời câu lân cận (A1) | Abstention 1/3, false abstention 0/22 (A0) | Abstention 3/3, false abstention 0/22 (A1, A2) |
| E2: q11, q12 | Retrieval: chunk chứa đáp án không có trong top-10 (q11) / rank 9 (q12); context miss. Agent A0 phải search lần 2 | Strategy B cắt câu dẫn "in most advanced countries, the following will be pretty generally applicable:" (chunk …52fa29, hybrid rank 1) khỏi danh sách đánh số "1. Abolition of property in land…" (chunk …e40031). Query khớp câu dẫn, đáp án nằm ở chunk kế tiếp | Thêm neighbour chunk (trước/sau, ±1 trang) vào context; budget 4500 (C1b, A2). Đối chứng: chỉ tăng budget 4500 không neighbour | Ctx Evidence 19/22; agent 2 search/câu, ~$0.00072/câu (A0) | Ctx Evidence 21/22 (budget-only: 19/22); agent 1 search, ~$0.00048/câu (A2) |
| E3: q06 (còn lại) | Paraphrase: hybrid đưa chunk đúng ở rank 7 → context miss ở mọi cấu hình retrieval | Câu hỏi diễn đạt lại ("group of intellectuals… decisive hour") ít trùng từ khóa; dense cũng không xếp cao | Không sửa riêng; với A2 agent vẫn tìm được trong 1 search (neighbour), A0/A1 cần 2 search | Ctx miss | Agent đúng (A0–A2); retrieval vẫn miss → giới hạn |

## Đánh đổi
- Neighbour + budget 4500 tăng context ~1450 ký tự/câu (≈ +360 token) và token input agent +20% (48k → 58k), nhưng giảm số search ở câu khó; chi phí tổng dev +$0.002 (A1 → A2), latency không đổi (≈3.5 s).
- Neighbour với budget 3000 làm mất evidence q18 (neighbour chiếm chỗ) → cần nâng budget khi bật neighbour.
- Filter chương (do người dùng cung cấp) gần như không đổi kết quả trên dev (chỉ dense +1 câu context).
- Toàn bộ thử nghiệm agent dev (A0+A1+A2 + smoke) tốn $0.044 theo `results/cost_ledger.jsonl`.

## Chọn cấu hình (theo `configs/selected_criteria.md`, commit a6d895f)
1. Pass dev: A1 = A2 = 25/25 > A0 = 23/25 → loại A0.
2. Context Evidence Rate: A2 (hybrid + neighbours, 4500) 21/22 > A1 (hybrid, 3000) 19/22 → **chọn A2**.
Ràng buộc: false abstention 0/22 (không tăng); median 3.6 s ≤ 10 s; $0.00062/câu ≤ $0.002; 0 lỗi hệ thống.

## Vòng 2 (sau khi test v1 bị dùng để chẩn đoán t06) — chỉ chỉnh trên dev, tiêu chí `configs/selected_criteria_v2.md` (commit b97e76a), đánh giá độc lập bằng test v2 (commit b62fa16)

### Retrieval dev

| Cấu hình | Hit@1 | Hit@3 | Context Evidence Rate | Median ms |
|---|---|---|---|---|
| A2 retriever: hybrid k5 + neighbours, 4500 | 18/22 | 19/22 | 21/22 (95.5%) | 44.1 |
| + I1 dedup text | 18/22 | 19/22 | 21/22 (95.5%) | 41.2 |
| + I3 top-k 8, 6000 | 18/22 | 19/22 | 22/22 (100.0%) | 43.0 |
| + I1 + I3 | 18/22 | 19/22 | 22/22 (100.0%) | 45.9 |

### Agent dev (tất cả cấu hình)

| Cấu hình | Pass | Grade 2 | Abstention đúng | False abstention | Citation hỗ trợ | Search TB | Median s | Token in/out | Chi phí (tổng / câu) |
|---|---|---|---|---|---|---|---|---|---|
| A0_hybrid_k5_s3 | 23/25 | 22/22 | 1/3 | 0/22 | 34/34 | 1.36 | 3.9 | 48727/3535 | $0.0140 / $0.00056 |
| A1_hybrid_v2 | 25/25 | 22/22 | 3/3 | 0/22 | 28/28 | 1.28 | 3.5 | 48069/3057 | $0.0133 / $0.00053 |
| A2_hybrid_v2_nb | 25/25 | 22/22 | 3/3 | 0/22 | 28/28 | 1.24 | 3.6 | 57600/3249 | $0.0154 / $0.00062 |
| A3_hybrid_v3_k8_nb_dd | 24/25 | 22/22 | 2/3 | 0/22 | 32/32 | 1.28 | 3.2 | 75840/3465 | $0.0193 / $0.00077 |
| A3b_hybrid_v2_k8_nb_dd | 25/25 | 22/22 | 3/3 | 0/22 | 29/29 | 1.2 | 3.7 | 66057/3150 | $0.0170 / $0.00068 |

### Kết luận vòng 2
- **I1 (gộp chunk trùng text)**: Day 6 có 7 đoạn bị lưu 2 lần (167 chunk, 7 bản sao). Không đổi chỉ số dev (không câu dev nào dính chunk trùng) → giữ vì lý do tổng quát (giải phóng chỗ trong top-k), không làm giảm chỉ số nào.
- **I3 (top-k 8)**: Context Evidence Rate dev 21/22 → **22/22** (q06 lần đầu vào context); agent: q06/q11/q12 vẫn 1 search. Chi phí +~10%/câu.
- **I2 (prompt v3: cấm tự tính số/ngày + bắt search lại)**: **làm xấu đi** — qn03 quay lại soft abstention ('closest formulation is…'), abstention 3/3 → 2/3. Giả thuyết: luật 8 ('search again… if any part still not supported, abstain') khiến model tìm 'phần gần nhất' và trả lời. → **Loại**. Lỗi suy luận số (t06 test v1) vẫn chưa có cách sửa được kiểm chứng; ghi vào giới hạn.
- Model reasoning không đặt temperature → kết quả có dao động giữa các lần chạy (qn03 với prompt v2: abstain ở A1, A2, A3b).
- **Chọn A3b** (theo tiêu chí v2): pass 25/25 = A2 (không thấp hơn), Context Evidence Rate 22/22 > 21/22. Ràng buộc: false abstention 0/22, chi phí ≤ $0.002/câu, 0 lỗi.
