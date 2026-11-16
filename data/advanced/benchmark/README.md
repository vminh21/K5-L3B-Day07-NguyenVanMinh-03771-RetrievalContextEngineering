# Benchmark — thử thách nâng cao (NASA FY 2024 AFR)

- Viết bằng cách **đọc trang gốc** (render 100–110 dpi, kiểm tra bằng mắt) **trước** khi xây index hay thử pipeline; commit trước mọi thí nghiệm.
- `page` = số trang PDF (số in trên trang = `page − 1`). Mỗi `quote` được script kiểm tra có trong text layer của đúng trang; evidence chỉ có trong hình (cột màu, đường nét đứt, nhãn trong ảnh raster như bản đồ trang 12, sơ đồ trang 39–40) ghi `visual_only: true` + `locator`.
- Câu thiếu evidence: `grep_checked` là các mẫu regex đã kiểm tra **không** xuất hiện trong toàn bộ 127 trang (script assert).

| Split | Bảng | Ảnh/sơ đồ | Biểu đồ | Multi-hop | Text | Thiếu evidence | Tổng |
|---|---:|---:|---:|---:|---:|---:|---:|
| test | 6 | 5 | 5 | 4 | 4 | 6 | **30** |
| dev | 3 | 3 | 4 | 2 | 3 | 3 | **18** |

Chấm test: mỗi câu **đạt / không đạt** theo ADVANCED.md §3 (đúng và đủ, đúng đơn vị; citation đúng trang chứa evidence; câu thiếu evidence phải từ chối). Lỗi hệ thống = không đạt. Ngưỡng: ≥ 27/30.

Sinh lại: `python -m src.mm.build_benchmark`.
