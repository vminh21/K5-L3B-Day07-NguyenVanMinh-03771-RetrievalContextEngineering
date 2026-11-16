# Cách chạy Day 7 — 2A202603771 Nguyễn Văn Minh

> File riêng của bài làm; `README.md` của ban tổ chức được giữ nguyên.


Báo cáo: [`report/individual/2A202603771_NguyenVanMinh.md`](report/individual/2A202603771_NguyenVanMinh.md). Corpus: *Manifesto of the Communist Party* (Public Domain) — index Day 6 strategy B, 167 chunk ([`data/day7/SOURCE.md`](data/day7/SOURCE.md)). Agent model: API **`gpt-5.6-luna`** (OpenAI Responses API).

## 1. Hạ tầng và môi trường
```bash
# Postgres + pgvector của Day 6 (repo Day 6 nằm cạnh repo này)
cd ../K5-L3B-Day06-NguyenVanMinh-2A202603771-DataIngestion/starter
docker compose -p day6_student_starter up -d --wait
ollama list                       # cần embeddinggemma (embedding 768 chiều)
cd -

python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env              # điền mật khẩu DB và OPENAI_API_KEY (không commit .env)
.venv/bin/python -m unittest discover -s tests -v   # unit test (mock chỉ dùng ở đây)
.venv/bin/python -m src.smoke_test                  # dense search trên pgvector Day 6
.venv/bin/python -m src.check_llm                   # kiểm tra key + model + 1 tool call (~$0.0001)
```
Trần chi phí API: `MAX_COST_USD` trong `.env` (mặc định $1, cộng dồn trong `results/cost_ledger.jsonl`).

## 2. Dữ liệu và benchmark
```bash
.venv/bin/python -m src.export_day6 --strategy B        # -> data/day7/chunks.json
.venv/bin/python -m src.build_benchmark                 # -> data/day7/{questions,cases}.json (dev + test v1)
.venv/bin/python -m src.build_benchmark --test-v2       # -> data/day7/test_v2/ (test độc lập vòng 2)
.venv/bin/python -m src.build_benchmark --round3        # -> data/day7/test_v3/ (20+6) và data/day7/dev_hard/ (8+2)
```

## 3. Retrieval trên dev (local, $0)
```bash
for m in dense bm25 hybrid; do .venv/bin/python -m src.eval_retrieval --method $m --split dev; done
.venv/bin/python -m src.eval_retrieval --method hybrid --split dev --budget 4500 --neighbors
.venv/bin/python -m src.eval_retrieval --method hybrid --split dev --top-k 8 --budget 6000 --neighbors --dedup-text
.venv/bin/python -m src.retrieve --method hybrid --top-k 3 "your question"     # thử một câu
```

## 4. Agent trên dev (API)
```bash
.venv/bin/python -m src.run_agent --split dev --method hybrid --config A0_hybrid_k5_s3
.venv/bin/python -m src.run_agent --split dev --method hybrid --prompt v2 --config A1_hybrid_v2
.venv/bin/python -m src.run_agent --split dev --method hybrid --prompt v2 --neighbors --per-search-budget 4500 --budget 9000 --config A2_hybrid_v2_nb
.venv/bin/python -m src.run_agent --split dev --method hybrid --prompt v2 --neighbors --dedup-text --top-k 8 --per-search-budget 6000 --budget 12000 --config A3b_hybrid_v2_k8_nb_dd
```
Chấm thủ công vào `results/agent/<config>/<split>/reviews.json`, rồi tổng hợp:
```bash
.venv/bin/python starter/agent_metrics.py --cases data/day7/cases.json \
  --traces results/agent/<config>/dev/traces.json --reviews results/agent/<config>/dev/reviews.json \
  --split dev --output results/agent/<config>/dev/agent_metrics.json
```

## 5. Test (chỉ sau khi chốt cấu hình)
Lệnh chính xác nằm trong [`configs/selected.json`](configs/selected.json) (vòng 1, test v1) và [`configs/selected_v2.json`](configs/selected_v2.json) (vòng 2, test v2). Test v2 dùng thêm `--cases data/day7/test_v2/cases.json --out-split test_v2` (agent) và `--questions data/day7/test_v2/questions.json` (retrieval); `agent_metrics.py` dùng `--cases data/day7/test_v2/cases.json`.

## 6. Vòng 3 (top-k giữ = 5) — cấu hình chốt: [`configs/selected_v3.json`](configs/selected_v3.json)
```bash
CS=data/day7/test_v3/cases.json; Q=data/day7/test_v3/questions.json
# retrieval test v3
.venv/bin/python -m src.eval_retrieval --method dense  --split test --questions $Q --budget 3000 --config dense_k5_b3000_TESTV3
.venv/bin/python -m src.eval_retrieval --method hybrid --split test --questions $Q --budget 4500 --neighbors --config hybrid_k5_b4500_nb_TESTV3
# agent test v3: A0 (baseline), A2 (đã chọn), A4 (ablation: bộ kiểm tra số + dedup)
.venv/bin/python -m src.run_agent --split test --cases $CS --out-split test_v3 --method dense --prompt v1 --per-search-budget 3000 --budget 6000 --config A0_dense_baseline
.venv/bin/python -m src.run_agent --split test --cases $CS --out-split test_v3 --method hybrid --prompt v2 --neighbors --per-search-budget 4500 --budget 9000 --config A2_hybrid_v2_nb
.venv/bin/python -m src.run_agent --split test --cases $CS --out-split test_v3 --method hybrid --prompt v2 --neighbors --dedup-text --verify-numbers --per-search-budget 4500 --budget 9000 --config A4_hybrid_v2_nb_dd_vn
.venv/bin/python starter/agent_metrics.py --cases $CS --traces results/agent/A2_hybrid_v2_nb/test_v3/traces.json \
  --reviews results/agent/A2_hybrid_v2_nb/test_v3/reviews.json --split test --output results/agent/A2_hybrid_v2_nb/test_v3/agent_metrics.json
# thử nghiệm đã loại trên dev: --method rerank (cross-encoder, cần sentence-transformers), --continuation-first
# chấm lại retrieval từ trace sau khi bổ sung gold: python -m src.rescore_retrieval results/retrieval/<cfg>/<split> <questions.json>
```
Dev khó: thay `$CS`/`$Q` bằng `data/day7/dev_hard/...` và `--split dev --out-split dev_hard`.

## Kết quả
- Dev: [`results/dev_experiments.md`](results/dev_experiments.md) · Test v1: [`results/test_results.md`](results/test_results.md) · Test v2: [`results/test_v2_results.md`](results/test_v2_results.md) · Test v3: [`results/test_v3_results.md`](results/test_v3_results.md)
- Trình tự commit chứng minh không chỉnh trên test: `e70e0a3` (đóng băng benchmark) → `5a097a5` (tiêu chí) → `2f28739` (chốt vòng 1) → test v1 → `6fa2c93` (test v2) → `00b50c5` (tiêu chí vòng 2) → `af9cdc7` (chốt vòng 2) → `b521b4a` (kết quả test v2) → `e6e0513` (test v3 + dev_hard) → `b8fc17a` (tiêu chí vòng 3) → `9a22c64` (phụ lục) → `7b8354e` (chốt vòng 3) → `83b6555` (kết quả test v3).
