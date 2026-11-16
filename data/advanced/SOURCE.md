# Tài liệu cho thử thách nâng cao

| Mục | Giá trị |
|---|---|
| Tài liệu | **NASA Fiscal Year 2024 Agency Financial Report (AFR)** |
| Tác giả / nhà xuất bản | National Aeronautics and Space Administration (NASA), Office of the Chief Financial Officer |
| Link gốc | https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr.pdf (trang danh mục: https://www.nasa.gov/organizations/budget-annual-reports/agency-financial-reports/) |
| Phiên bản | Bản PDF tải ngày 2026-11-16, 16 MB, PDF 1.7, SHA-256 `65ee29adf5f3a92fcd74701696c25dae8f2d18f1ba2e7f4fba2bcfc059acbefc` |
| Số trang | **127 trang**, index toàn bộ (trang 1–127) |
| Nội dung | Text (MD&A, kiểm toán, OIG), **56 bảng** trên 32 trang (báo cáo tài chính, thuyết minh, grant, penalty), **biểu đồ** vector (cột, cột chồng, donut), **sơ đồ** (tổ chức, khung chiến lược, kim tự tháp FMFIA, ERM), **bản đồ** các trung tâm, infographic, ảnh có chú thích |
| Quyền sử dụng | Tác phẩm của cơ quan liên bang Hoa Kỳ — không thuộc bản quyền tại Mỹ (17 U.S.C. §105), theo NASA Media Usage Guidelines. Một số ảnh có thể của bên thứ ba (ghi photo credit). PDF **không được commit** (16 MB); tải lại bằng lệnh dưới đây và kiểm tra SHA-256 |

```bash
mkdir -p data/advanced/raw && curl -sL -A "Mozilla/5.0" -o data/advanced/raw/nasa_afr_fy2024.pdf \
  "https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr.pdf"
shasum -a 256 data/advanced/raw/nasa_afr_fy2024.pdf   # phải ra 65ee29adf5f3a92fcd74701696c25dae8f2d18f1ba2e7f4fba2bcfc059acbefc
```

Đã thử và loại hai tài liệu khác: *World Development Report 2024* (276 trang nhưng chỉ 5 bảng) và *Python Image Processing Cookbook* (Packt 2020; chỉ 2 bảng thật, giữ toàn quyền tác giả).
