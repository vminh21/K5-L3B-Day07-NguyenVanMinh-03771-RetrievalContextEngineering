# Sửa lỗi đo Context Evidence Rate (phát hiện ở vòng 3, 2026-11-16)

**Lỗi:** `context_has_evidence()` lấy trang của context chỉ từ các chunk *được retrieve*; chunk **neighbour** (thêm vào context nhưng không nằm trong danh sách retrieve) bị bỏ qua khi xét trang. Nếu evidence nằm trong neighbour ở **trang khác**, câu bị tính là context miss dù evidence có trong context.

**Sửa:** lấy trang từ **mọi** chunk ID trong context (`src/eval_retrieval.py`). Script `src/rescore_retrieval.py` vốn đã đúng.

**Ảnh hưởng (chỉ các cấu hình có neighbour):**

| Cấu hình | Split | Context Evidence Rate cũ → đúng | Câu thay đổi |
|---|---|---|---|
| Hybrid + neighbours, k5, 3000 | dev | 20/22 → **21/22** | q06 |
| Hybrid + neighbours, k5, 4500 (A2) | dev | 21/22 → **22/22** | q06 |
| Hybrid + neighbours + dedup, k5, 4500 | dev | 21/22 → **22/22** | q06 |
| Hybrid + neighbours (± dedup), k8, 6000 (A3b) | dev | 22/22 → 22/22 | — |
| Mọi cấu hình neighbour | test v1, test v2 | không đổi (chấm lại từ trace) | — |

**Hệ quả với kết luận vòng 2:** "top-k 8 nâng Context Evidence Rate dev 21/22 → 22/22" là **sai do lỗi đo** — A2 (k5) thực ra đã 22/22. Theo `selected_criteria_v2.md`, A2 và A3b hòa ở tiêu chí 1–4 → lẽ ra chọn cấu hình **rẻ hơn = A2**. Lựa chọn A3b ở vòng 2 vì vậy không được dữ liệu ủng hộ; ghi nhận trong báo cáo. (Vòng 3 không dùng top-k 8 theo yêu cầu.)
