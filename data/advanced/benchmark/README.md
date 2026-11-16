# Benchmark — thử thách nâng cao (NASA FY 2024 AFR)

- Viết bằng cách **đọc trang gốc** (render 100–110 dpi, kiểm tra bằng mắt) **trước** khi xây index hay thử pipeline; commit trước mọi thí nghiệm.
- `page` = số trang PDF (số in trên trang = `page − 1`). Mỗi `quote` được script kiểm tra có trong text layer của đúng trang; evidence chỉ có trong hình (cột màu, đường nét đứt, nhãn trong ảnh raster như bản đồ trang 12, sơ đồ trang 39–40) ghi `visual_only: true` + `locator`.
- Câu thiếu evidence: `grep_checked` là các mẫu regex đã kiểm tra **không** xuất hiện trong toàn bộ 127 trang (script assert).

| Split | Bảng | Ảnh/sơ đồ | Biểu đồ | Multi-hop | Text | Thiếu evidence | Tổng |
|---|---:|---:|---:|---:|---:|---:|---:|
| test | 6 | 5 | 5 | 4 | 4 | 6 | **30** |
| dev v1 | 3 | 3 | 4 | 2 | 3 | 3 | 18 |
| dev v2 (thêm) | 0 | 2 | 2 | 2 | 2 | 2 | 10 |
| **dev tổng** | 3 | 5 | 6 | 4 | 5 | 5 | **28** |

Chấm test: mỗi câu **đạt / không đạt** theo ADVANCED.md §3 (đúng và đủ, đúng đơn vị; citation đúng trang chứa evidence; câu thiếu evidence phải từ chối). Lỗi hệ thống = không đạt. Ngưỡng: ≥ 27/30.

Sinh lại: `python -m src.mm.build_benchmark`.

**Dev v2** (`D2-*`) được thêm sau khi dev v1 bão hòa (18/18 với mọi cấu hình, xem `results/advanced/*/dev`), **trước** mọi lần chạy test; dùng phần tử/đáp án khác test nhưng cùng dạng khó (chỉ có trong hình, bản đồ raster → infographic, biểu đồ → biểu đồ). Test không đổi (`git diff` của `test.json` rỗng).

## Quy tắc chấm bổ sung (ghi trước khi chạy test)

- **Evidence thay thế:** báo cáo lặp số liệu ở nhiều nơi (ví dụ net cost theo goal có ở biểu đồ p32 **và** bảng Statement of Net Cost p51). Citation tới trang khác `evidence` vẫn đạt nếu nội dung **bản gốc** của trang đó hỗ trợ toàn bộ phần được trích; người chấm mở trang gốc để kiểm tra và ghi lại trong `labels.json`. Phát hiện ở dev D2-MH2.
- **Chi tiết thừa trong đáp án mẫu** (ví dụ "12%", "$24.9B" khi câu hỏi không hỏi) không bắt buộc; auto-check chỉ là gợi ý.
