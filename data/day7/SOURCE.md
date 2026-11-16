# Corpus nguồn — Day 7 (phần cơ bản)

| Trường | Giá trị |
|---|---|
| Tài liệu | *Manifesto of the Communist Party* — Karl Marx & Frederick Engels |
| Bản dịch | Samuel Moore (1888), cùng Frederick Engels |
| Phiên bản | Marxists Internet Archive (marxists.org) 2005 PDF; từ Marx/Engels Selected Works, Vol 1, Progress Publishers, 1969 |
| URL gốc | https://www.marxists.org/archive/marx/works/1848/communist-manifesto/ |
| Quyền sử dụng | Public Domain (Marxists Internet Archive) |
| Số trang | 44 trang vật lý; trang 1 (bìa/thông tin xuất bản) bị loại; **43 trang nội dung (2–44)** |
| Ngôn ngữ | English |
| `source_id` | `communist-manifesto-1848` |

## Index sử dụng (tái dùng Day 6)

| Trường | Giá trị |
|---|---|
| Vector store | PostgreSQL 16 + pgvector **0.8.7** (`pgvector/pgvector:0.8.7-pg16`), Docker project `day6_student_starter`, cổng `127.0.0.1:55433`, DB `day6_lab`, bảng `chunks` |
| Strategy | **B** — paragraph-aware, tối đa 1000 ký tự, overlap 0 (strategy được chọn ở báo cáo Day 6: coherence 2.0/2) |
| Số chunk | **167** (trang 2–44), ID duy nhất |
| Embedding | `embeddinggemma` qua Ollama local, **768 chiều**, cosine |
| Prefix | document: `title: Manifesto of the Communist Party \| text: …`; query: `task: search result \| query: …` |
| Export | `python -m src.export_day6 --strategy B` → `data/day7/chunks.json` (2026-11-16, sha256 `6b63e91f038836e6…`) |

## Ghi chú

- Báo cáo Day 6 ghi 158 chunk cho strategy B, nhưng database hiện tại có **167** chunk B (273 A / 167 C) — DB đã được ingest lại sau khi viết báo cáo. Day 7 dùng **đúng nội dung trong DB** (167 chunk) làm nguồn chuẩn, vì dense retrieval đọc trực tiếp DB.
- Trường `source` trong DB là đường dẫn tuyệt đối trên máy tác giả; khi export được đổi thành đường dẫn tương đối `K5-L3B-Day06-…/data/manifest.pdf`. `id`, `page`, `text`, `metadata` giữ nguyên.
- Dense (đọc DB) và các phương pháp lexical (đọc `chunks.json`) dùng **cùng 167 chunk ID** — đã kiểm tra: 30/30 kết quả dense nằm trong `chunks.json`.
- Metadata có `chapter`/`section` (dùng được cho filter khi người dùng cung cấp).
