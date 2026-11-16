# Tiêu chí chọn cấu hình — vòng 3 (viết TRƯỚC khi đo)

Ngày: 2026-11-16. Chỉnh trên **dev (25 câu) + dev_hard (10 câu)**; đánh giá độc lập bằng **test v3** (commit e6e0513), chạy một lần sau khi chốt. Test v1 (t06) chỉ dùng làm **chẩn đoán** (đã bị dùng để chỉnh từ vòng 2), không dùng để chọn.

## Ràng buộc của người dùng
- **Không sửa lỗi bằng cách lấy thêm chunk**: top-k = 5 như A2 (không dùng top-k 8 của vòng 2).

## Cải tiến dự kiến (tổng quát)
- **I4 — rerank bằng cross-encoder** (`cross-encoder/ms-marco-MiniLM-L-6-v2`, local, $0): hybrid lấy 20 ứng viên → cross-encoder xếp lại → vẫn lấy **5**. Giả thuyết: chunk đúng bị RRF xếp hạng thấp (t06 hạng 10, q06 hạng 7) sẽ lên top-5 mà không tăng số chunk.
- **I5 — kiểm tra số liệu trong câu trả lời** (deterministic): mọi số/năm trong câu trả lời phải có trong passage được cite (so khớp cả chữ số và số viết bằng chữ). Sai → yêu cầu model sửa một lần; vẫn sai → abstain. Giả thuyết: chặn lỗi tự tính số (t06 "1873") mà không phụ thuộc prompt (prompt v3 đã thất bại).
- **I1 — gộp chunk trùng text** (giữ từ vòng 2; không tăng số chunk).

## Thứ tự ưu tiên
1. **Pass trên dev_hard** (grade 2 + abstention đúng, /10).
2. **Pass trên dev** (/25) — không được thấp hơn A2 (25/25) quá 1 câu.
3. Context Evidence Rate retrieval trên dev + dev_hard (multi-hop: đủ mọi nhóm).
4. Evidence Hit@3 dev + dev_hard.
5. Hòa → rẻ hơn, rồi nhanh hơn.

## Ràng buộc khác
- False abstention ≤ 1 trên (22 + 8) câu có đáp án; median latency ≤ 10 s/câu; chi phí ≤ $0.002/câu; 0 lỗi hệ thống.
- Cải tiến làm giảm chỉ số dev → loại, kể cả khi sửa được t06.

## Test v3
Chạy một lần: A0 (baseline), A2 (chọn vòng 1), cấu hình chọn vòng 3.

## Phụ lục (viết sau khi đo vòng 3 lần 1, TRƯỚC khi đo lần 2) — 2026-11-16
Kết quả lần 1: dev_hard A2 = A4 = A4r = 10/10; dev A2 25/25, A4 24/25 (q12 false abstention).
- Chẩn đoán q12: bộ kiểm tra số **không kích hoạt**; replay cùng query cho context **giống hệt** khi bật/tắt dedup → nguyên nhân là query model tự chọn (dao động giữa các lần chạy), không phải thành phần A4.
- A4r (rerank): retrieval dev CtxEv 22 → 19/22, dev_hard 8 → 6/8 → **loại** (giảm chỉ số dev).
- Continuation-first: dev 22/22, dev_hard 8 → 7/8 (h04: evidence ở neighbour không bị cắt) → **loại**.
- Vì khác biệt A2/A4 chỉ là 1 câu do dao động, **đo thêm 1 lần nữa trên dev cho cả A2 và A4** (cùng code, gồm bản sửa `exclude` cho neighbour đã hiển thị); báo cáo **cả hai lần**, quyết định theo **tổng pass 2 lần** (/50), hòa → tiêu chí cũ tiếp theo. Không chạy thêm lần nào nữa.
