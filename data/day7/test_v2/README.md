# Test v2 — bộ test độc lập mới

**Lý do tạo:** Sau khi chạy test v1 (commit `0a61773` chốt cấu hình A2), câu t06 của A2 chỉ đúng một phần. Bài làm quyết định cải tiến hệ thống dựa trên lỗi này. Theo RULES.md ("Nếu đã xem test để chỉnh, tạo test mới và ghi rõ") và BENCHMARK.md dòng 17, **test v1 không còn là đánh giá độc lập** cho các cấu hình được chỉnh sau thời điểm đó.

- Test v1 (`data/day7/questions.json` / `cases.json`, split `test`, 6 + 2 câu) giữ nguyên làm bằng chứng; kết quả A0/A2 trên test v1 vẫn được báo (`results/test_results.md`).
- Test v2 (thư mục này, 7 câu có đáp án + 2 câu thiếu evidence) được **viết và commit trước** khi thay đổi hoặc đánh giá bất kỳ cấu hình mới nào, chỉ dùng các trang chưa xuất hiện trong dev hoặc test v1 (17, 19, 22, 27, 31, 38, 43).
- Sinh lại: `python -m src.build_benchmark --test-v2`. Evidence đã qua `validate()` của starter.
- Cấu hình mới chỉ được chỉnh trên **dev**; test v2 chạy **một lần** sau khi chốt.
