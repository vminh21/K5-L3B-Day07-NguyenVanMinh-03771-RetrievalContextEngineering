# Kết quả TEST (chạy 1 lần sau khi chốt cấu hình ở commit 0a61773) — 2026-11-16

## Retrieval (6 câu có đáp án)

| Cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | MRR@10 | Context thủ công 0/1/2 (TB) | Median ms |
|---|---|---|---|---|---|---|
| M1 Dense (baseline) | 3/6 (50.0%) | 5/6 (83.3%) | 6/6 (100.0%) | 0.681 | 0/0/6 (2.0) | 49.6 |
| Hybrid RRF + neighbours, 4500 (selected) | 4/6 (66.7%) | 5/6 (83.3%) | 5/6 (83.3%) | 0.767 | 1/0/5 (1.67) | 45.7 |

## Agent (gpt-5.6-luna, 8 câu test = 6 có đáp án + 2 thiếu evidence; nhãn thủ công `reviews.json`)

| Cấu hình | Tool use | Số search/câu (phân bố) | Grounded 0/1/2 (TB /2) | Citation hỗ trợ | Câu trả lời có citation | Abstention đúng | Từ chối nhầm | Lỗi hệ thống | Median s | Token in/out | Chi phí |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 baseline | 8/8 | {1: 5, 2: 2, 3: 1} | 0/0/6 (2.00) | 7/7 | 6/6 | 2/2 | 0/6 | 0 | 5.5 | 17028/1014 | $0.0046 |
| A2 selected | 8/8 | {1: 5, 2: 1, 3: 2} | 0/1/5 (1.83) | 7/7 | 6/6 | 2/2 | 0/6 | 0 | 4.4 | 27786/1368 | $0.0072 |

Pass (grade 2 + abstention đúng): A0 **8/8**, A2 **7/8** (t06 grade 1).

## Lỗi hệ thống (báo riêng)
- A2 lần chạy test thứ 1: 8/8 câu `APIConnectionError` (máy không phân giải được DNS `api.openai.com`; `google.com` vẫn truy cập được). 0 câu trả lời, $0. Trace giữ ở `results/agent/A2_hybrid_v2_nb/test_attempt1_connection_error/`. Sau khi DNS tự phục hồi, chạy lại **một lần** (kết quả ở bảng trên). Không có lần chạy nào khác trên test.
- Retrieval test: 0 lỗi.

## Phát hiện trên test
- **t06 (A2 sai một phần):** retriever đã chọn (hybrid + neighbours) đưa chunk gold xuống rank 10 → context không có evidence (context 0); dense baseline có ở rank 4. Agent A2 không abstain mà trả lời một phần từ preface 1890 (1864, 'lived only nine years') và **tự tính '1873'**, trái với tài liệu (1874). → Cấu hình chọn trên dev không tốt hơn baseline trên test 6 câu; prompt v2 chưa ngăn được suy luận số học ngoài evidence.
- **Gold chưa đủ:** p41 (…b1a3da, preface 1890) cũng là evidence hợp lệ cho t06 ('The working class of 1874 … altogether different from that of 1864'). Không sửa gold sau khi xem test; citation này được chấm hỗ trợ trong review A0 và ghi là giới hạn benchmark.
- **Chunk trùng ở Day 6:** p41 …4c2ec7 và …2d6d9b có nội dung giống hệt nhau (ingest lặp), chiếm 2 chỗ trong top-k.
- Test chỉ 6 câu có đáp án → 1 câu = 16.7 điểm %, khác biệt giữa cấu hình không có ý nghĩa thống kê.

## Chi phí
- Test: A0 $0.0046, A2 $0.0072. Tổng toàn bộ API từ đầu: xem `results/cost_ledger.jsonl`.
