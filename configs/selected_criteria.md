# Tiêu chí chọn cấu hình (viết TRƯỚC khi so sánh các cấu hình cải thiện trên dev)

Ngày: 2026-11-16. Chỉ dùng **dev** (22 câu có đáp án + 3 câu thiếu evidence). Test không được chạy cho tới khi `configs/selected.json` được commit.

Baseline đã đo: retrieval M1–M3 (`results/retrieval/dev_comparison.md`) và agent A0 = hybrid RRF, top-5, max 3 search, prompt v1 (`results/agent/A0_hybrid_k5_s3/dev`).

## Thứ tự ưu tiên
1. **Agent dev pass** (cao hơn tốt hơn) = số câu có đáp án được chấm `answer_grade = 2` + số câu thiếu evidence `abstention_correct = true`, trên 25 câu.
2. **Retrieval Context Evidence Rate** dev của retriever/context mà cấu hình dùng.
3. **Evidence Hit@3** dev.
4. **Citation validity** (citation được chấm hỗ trợ / tổng citation).
5. Hòa → chọn cấu hình **rẻ hơn**, rồi **nhanh hơn** (median latency).

## Ràng buộc (loại cấu hình nếu vi phạm)
- False abstention trên 22 câu có đáp án không tăng quá 1 câu so với A0 (A0 = 0/22).
- Median latency agent ≤ 10 s/câu; chi phí trung bình ≤ $0.002/câu (gpt-5.6-luna, giá ghi trong summary).
- 0 lỗi hệ thống trên dev (nếu có lỗi → chạy lại sau khi sửa hạ tầng, ghi lại).

## Ghi chú
- Kết quả không cải thiện vẫn được báo.
- Không chỉnh cấu hình sau khi xem test; nếu lỡ xem → viết test mới và ghi rõ trong báo cáo.
