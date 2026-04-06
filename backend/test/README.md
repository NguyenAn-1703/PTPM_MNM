# Backend Test Scripts

Quick reference for utility scripts in this folder.

## Script list

| Script | Purpose | Typical command |
|---|---|---|
| `test_ocr.py` | Check local Tesseract setup and languages. | `python3 test/test_ocr.py` |
| `test_api_smoke.py` | Smoke test core API endpoints (`status`, invalid `chat`, invalid `clear memory`). | `python3 test/test_api_smoke.py --base-url http://127.0.0.1:8000/api` |
| `test_owner_session_distribution.py` | Show `owner_session_id` distribution in source registry and FAISS docstore. | `python3 test/test_owner_session_distribution.py --top 10` |
| `test_owner_session_remap.py` | Smoke test `remap_owner_session_id` command in dry-run mode. | `python3 test/test_owner_session_remap.py --from-owner legacy --to-owner user123` |
| `test_chunk_strategy.py` | Evaluate chunk size/overlap combinations. | `python3 test/test_chunk_strategy.py --evaluation-file evaluation_set.json` |
| `benchmark_retrieval_latency.py` | Benchmark retrieval latency by mode. | `python3 test/benchmark_retrieval_latency.py --iterations 3 --warmup 1` |
| `benchmark_stream_latency.py` | Benchmark SSE streaming latency (`ttfb`, first token, total). | `python3 test/benchmark_stream_latency.py --iterations 2 --max-questions 5` |
| `test_ragas_pipeline.py` | Run self-rag calibration pipeline (optional ragas). | `python3 test/test_ragas_pipeline.py --evaluation-file evaluation_set.json` |
| `run_test_suite.py` | Run many scripts from one command with quick/full presets. | `python3 test/run_test_suite.py --suite quick` |

## Suite runner shortcuts

| Goal | Command |
|---|---|
| Quick checks | `python3 test/run_test_suite.py --suite quick` |
| Full suite (exclude heavy by default) | `python3 test/run_test_suite.py --suite full` |
| Full suite + heavy scripts | `python3 test/run_test_suite.py --suite full --include-heavy` |
| Run only selected scripts | `python3 test/run_test_suite.py --only ocr,owner_distribution,owner_remap` |
| Strict mode (exit 1 on failures) | `python3 test/run_test_suite.py --suite quick --strict` |

## Notes

| Item | Detail |
|---|---|
| Server-required scripts | `test_api_smoke.py`, `benchmark_stream_latency.py` |
| Default API URL | `http://127.0.0.1:8000/api` |
| Heavy scripts | `test_chunk_strategy.py`, `benchmark_retrieval_latency.py`, `test_ragas_pipeline.py` |
| Evaluation set | Usually use `backend/evaluation_set.json` |
