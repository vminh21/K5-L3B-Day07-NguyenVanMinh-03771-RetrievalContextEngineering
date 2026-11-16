# Test v3 — kết quả (chạy một lần, 2026-11-16)

Cấu hình chốt trước khi chạy: `configs/selected_v3.json` (commit 89a611a). Benchmark: `data/day7/test_v3` (commit df55fb3), 20 câu có đáp án + 6 câu thiếu evidence.

## Retrieval (câu hỏi gốc, 20 câu có đáp án)
| Cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Miss context |
|---|---|---|---|---|
| Dense k5, 3000 (baseline) | 18/20 | 20/20 | **19/20** | v16 (multi-hop) |
| Hybrid + neighbour k5, 4500 (A2, đã chọn) | 16/20 | 19/20 | 18/20 | v01 (gold ở hạng 7), v16 |
| Hybrid + neighbour + dedup (retriever A4) | 16/20 | 19/20 | 18/20 | v01, v16 |

## Agent (26 câu, chấm tay — `results/agent/*/test_v3/reviews.json`)
| Cấu hình | Pass | Grounded 0/1/2 | Citation hợp lệ | Abstention đúng | False abstention | Chi phí | Median |
|---|---|---|---|---|---|---|---|
| A0 dense, prompt v1 | **26/26** | 0/0/20 | 25/25 | 6/6 | 0/20 | $0.0138 | 4.4 s |
| A2 (đã chọn) | **26/26** | 0/0/20 | 24/24 | 6/6 | 0/20 | $0.0150 | 3.6 s |
| A4 (ablation: + bộ kiểm tra số + dedup) | 25/26 | 1/0/19 | 21/21 | 6/6 | 1/20 (v07) | $0.0188 | 3.9 s |

- v07 (A4): gold …f4daba được retrieve ở hạng 3/5 nhưng bị neighbour của hit hạng cao đẩy khỏi budget → abstain (lỗi E5). Bộ kiểm tra số không kích hoạt; replay xác nhận dedup không phải nguyên nhân.
- Bộ kiểm tra số không kích hoạt lần nào trên test v3.
- Multi-hop v06, v10, v16: cả 3 cấu hình trả lời đủ hai phần, citation phủ cả hai nhóm.
- 6 câu bẫy thiếu evidence: cả 3 cấu hình abstain đúng.

## Chẩn đoán (không độc lập)
- t06 (test v1) chạy lại với A4: đúng (1864 / 1874), nhưng bộ kiểm tra số không kích hoạt — đúng nhờ query khác.
- Replay offline bộ kiểm tra số trên 296 câu trả lời đã lưu: 1 đúng (t06 "1873"), 4 false positive → `results/manual/numcheck_offline_replay.json`.
