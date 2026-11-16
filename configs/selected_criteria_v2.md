# Tiêu chí chọn cấu hình — vòng 2 (viết TRƯỚC khi đo các cải tiến mới)

Ngày: 2026-11-16. Bối cảnh: test v1 đã bị dùng để chẩn đoán lỗi t06 → chỉ chỉnh trên **dev**; đánh giá độc lập bằng **test v2** (commit b62fa16), chạy một lần sau khi chốt.

## Cải tiến dự kiến (tổng quát, không nhắm riêng một câu)
- **I1 — loại chunk trùng nội dung**: Day 6 có chunk giống hệt nhau chiếm chỗ trong top-k/context.
- **I2 — prompt v3**: cấm suy luận/tính toán số liệu, ngày tháng không ghi nguyên văn trong passage; nếu passage chỉ trả lời được một phần câu hỏi → search lại với cách diễn đạt khác; vẫn thiếu → abstain.
- **I3 — tăng độ sâu retrieval**: top-k mỗi lượt 5 → 8 (giữ neighbours), để chunk đúng ở hạng 6–8 vào được context.

## Thứ tự ưu tiên (trên dev)
1. Agent dev pass (grade 2 + abstention đúng) trên 25 câu — **không được thấp hơn A2 (25/25)**.
2. Retrieval Context Evidence Rate dev của retriever/context dùng trong cấu hình.
3. Evidence Hit@3 dev.
4. Citation validity.
5. Hòa → rẻ hơn, rồi nhanh hơn.

## Ràng buộc
- False abstention dev ≤ 1/22; median latency ≤ 10 s/câu; chi phí ≤ $0.002/câu; 0 lỗi hệ thống.
- Nếu một cải tiến không giúp/không đổi trên dev, vẫn có thể giữ khi nó **không làm giảm** chỉ số nào và có lý do tổng quát (ghi rõ); nếu làm giảm → bỏ.

## Test
- Chạy trên test v2: baseline A0 (đã chốt từ vòng 1), A2 (cấu hình chốt vòng 1) và cấu hình mới được chọn — mỗi cấu hình **một lần**.
