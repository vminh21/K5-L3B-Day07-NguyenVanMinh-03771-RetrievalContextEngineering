# Kết quả TEST v2 (đánh giá độc lập vòng 2) — 2026-11-16

Test v2 viết và commit trước mọi thay đổi (6fa2c93); cấu hình vòng 2 chốt trước khi chạy (af9cdc7). Mỗi cấu hình chạy **một lần**. Test v1 không còn độc lập cho cấu hình vòng 2 (đã dùng để chẩn đoán t06) — kết quả test v1 xem `results/test_results.md`.

## Retrieval (7 câu có đáp án)

| Cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | MRR@10 | Median ms |
|---|---|---|---|---|---|
| M1 Dense (baseline) | 5/7 (71.4%) | 7/7 (100.0%) | 7/7 (100.0%) | 0.833 | 45.1 |
| Hybrid + neighbours, k5 (A2) | 6/7 (85.7%) | 7/7 (100.0%) | 7/7 (100.0%) | 0.929 | 41.9 |
| Hybrid + neighbours + dedup, k8 (A3b, chọn vòng 2) | 6/7 (85.7%) | 7/7 (100.0%) | 7/7 (100.0%) | 0.929 | 50.7 |

Context thủ công (0/1/2): dense 0/0/7, A3b retriever 0/0/7 — `results/manual/context_review_test_v2.json`.

## Agent (gpt-5.6-luna; 9 câu = 7 có đáp án + 2 thiếu evidence; nhãn thủ công `reviews.json`)

| Cấu hình | Pass | Tool use | Search/câu | Grounded 0/1/2 (TB) | Citation hỗ trợ | Abstention đúng | Từ chối nhầm | Lỗi | Median s | Token in/out | Chi phí |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 baseline | 9/9 | 9/9 | {1: 7, 3: 2} | 0/0/7 (2.00) | 9/9 | 2/2 | 0/7 | 0 | 4.4 | 18967/1187 | $0.0052 |
| A2 (chọn vòng 1) | 9/9 | 9/9 | {1: 7, 2: 2} | 0/0/7 (2.00) | 9/9 | 2/2 | 0/7 | 0 | 3.5 | 20639/983 | $0.0053 |
| A3b (chọn vòng 2) | 9/9 | 9/9 | {1: 7, 2: 2} | 0/0/7 (2.00) | 8/8 | 2/2 | 0/7 | 0 | 3.7 | 24229/1004 | $0.0060 |

## Nhận xét
- Cả ba cấu hình đạt 9/9 trên test v2 → test v2 **không phân biệt được** các cấu hình; lợi ích của neighbours/top-k 8 (thấy ở dev q06, q11, q12; top-k 8 được thêm vì lỗi t06 của test v1 nhưng **chưa được kiểm chứng trên t06**, vì chạy A3b trên test v1 sẽ không còn độc lập) không xuất hiện vì 7 câu test v2 đều có evidence ở top-3 của mọi retriever.
- Kết hợp hai bộ test: A2 = 7/8 (v1) + 9/9 (v2); A0 = 8/8 + 9/9; A3b chỉ có kết quả độc lập trên v2 (9/9). Mẫu nhỏ (13 câu có đáp án) → không kết luận được cấu hình nào tốt hơn có ý nghĩa thống kê.
- A3b đắt hơn A0 ~15% token input/câu trên test v2 nhưng không cải thiện kết quả ở bộ này; lựa chọn A3b dựa trên dev (Context Evidence Rate 22/22) và lý do tổng quát.
- Gold test v2 cũng chưa đủ: u06 có câu tương đương ở preface 1890 (p41 …deebda). Không sửa gold sau khi chạy; mọi cấu hình đều cite p38 (gold) nên không ảnh hưởng điểm.
- 0 lỗi hệ thống. Tổng chi phí test v2: xem cột chi phí; tổng toàn bộ API: `results/cost_ledger.jsonl`.
