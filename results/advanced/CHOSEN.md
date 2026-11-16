# Cấu hình chốt cho test (quyết định trên dev, trước khi chạy test)

`mmC_rerank_k5_kind_view` = `python -m src.mm.run --split test --config mmC_rerank_k5_kind_view --method rerank`

| Cấu hình | Retrieval | Tool | Dev (chấm tay) | Chi phí dev |
|---|---|---|---:|---:|
| mmA_hybrid_k5 | hybrid RRF (dense pgvector + BM25), top-5 | search(query), final_answer | 28/28 | $0.0216 |
| mmB_rerank_k5_kind | hybrid RRF pool 30 → cross-encoder rerank, top-5 | search(query, kind), final_answer | 28/28 | $0.0269 |
| **mmC_rerank_k5_kind_view** | như B | search(query, kind), **view_page(page, focus)**, final_answer | 28/28 | $0.0303 |

Retrieval-only trên dev (`results/advanced/retrieval_dev.json`): dense / hybrid / rerank đều hit@3 = 1.0, MRR ≈ 0.97 → dev không phân biệt được.
Chọn C vì: hòa trên dev; `view_page` là đường dự phòng cho hình raster/màu (bản đồ p12, sơ đồ p39–40) khi bản chép thiếu; chênh chi phí ~$0.0003/câu.
Rerank **không** cho cải thiện đo được trên dev — ghi nhận trung thực.
