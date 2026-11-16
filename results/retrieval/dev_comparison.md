# Retrieval trên DEV (22 câu có đáp án, query gốc, không rewrite)

| Cấu hình | Phương pháp, top-k context, filter, budget | Hit@1 | Evidence Hit@3 | Context Evidence Rate | MRR@10 | Median ms / chi phí |
|---|---|---|---|---|---|---|
| M0 TF-IDF (starter, tham chiếu) | top-3, no filter, 800 ký tự | 16/22 (72.7%) | 18/22 (81.8%) | 6/22 (27.3%) | – | 0.2 / $0 |
| M1 Dense (pgvector Day 6) | top-5, no filter, 3000 ký tự | 15/22 (68.2%) | 18/22 (81.8%) | 18/22 (81.8%) | 0.767 | 46.6 / $0 |
| M1 Dense (pgvector Day 6) + filter | top-5, filter người dùng, 3000 ký tự | 15/22 (68.2%) | 18/22 (81.8%) | 19/22 (86.4%) | 0.778 | 41.8 / $0 |
| M2 BM25 | top-5, no filter, 3000 ký tự | 14/22 (63.6%) | 17/22 (77.3%) | 17/22 (77.3%) | 0.71 | 0.1 / $0 |
| M2 BM25 + filter | top-5, filter người dùng, 3000 ký tự | 14/22 (63.6%) | 17/22 (77.3%) | 17/22 (77.3%) | 0.715 | 0.1 / $0 |
| M3 Hybrid RRF (k=60, pool 20) | top-5, no filter, 3000 ký tự | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 0.852 | 40.8 / $0 |
| M3 Hybrid RRF (k=60, pool 20) + filter | top-5, filter người dùng, 3000 ký tự | 18/22 (81.8%) | 19/22 (86.4%) | 19/22 (86.4%) | 0.862 | 41.4 / $0 |

Nguồn số liệu: `results/retrieval/<config>/dev/summary.json`; trace từng câu trong `traces.json`.
Filter = trường `filter` của câu hỏi (4 câu dev: q07, q11, q14, q19), coi như người dùng cung cấp; không suy ra từ gold.
