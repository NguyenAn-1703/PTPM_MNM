

#  Backend Test Scripts Quick Guide

Tổng hợp các script tiện ích để debug và benchmark hệ thống RAG.

## 1. Danh sách Script

| Script | Mục đích | Câu lệnh mẫu |
|---|---|---|
| `test_ocr.py` | Kiểm tra cài đặt Tesseract và các ngôn ngữ hỗ trợ. | `python3 test/test_ocr.py` |
| `test_api_smoke.py` | Test nhanh các API core (trạng thái hệ thống, chat lỗi, xóa memory). | `python3 test/test_api_smoke.py --base-url http://127.0.0.1:8000/api` |
| `test_owner_session_distribution.py` | Thống kê phân bổ `owner_session_id` trong registry và FAISS. | `python3 test/test_owner_session_distribution.py --top 10` |
| `test_owner_session_remap.py` | Chạy thử lệnh đổi owner (dry-run) để kiểm tra logic. | `python3 test/test_owner_session_remap.py --from-owner legacy --to-owner user123` |
| `test_chunk_strategy.py` | Đánh giá các cấu hình chunk size/overlap (cắt đoạn văn bản). | `python3 test/test_chunk_strategy.py --evaluation-file evaluation_set.json` |
| `benchmark_retrieval_latency.py` | Đo độ trễ (latency) của các chế độ tìm kiếm (vector/hybrid). | `python3 test/benchmark_retrieval_latency.py --iterations 3 --warmup 1` |
| `benchmark_stream_latency.py` | Đo tốc độ stream SSE (thời gian ra chữ đầu tiên, tổng thời gian). | `python3 test/benchmark_stream_latency.py --iterations 2 --max-questions 5` |
| `test_ragas_pipeline.py` | Chạy pipeline đánh giá chất lượng RAG (cần thư viện Ragas). | `python3 test/test_ragas_pipeline.py --evaluation-file evaluation_set.json` |
| `run_test_suite.py` | Trình quản lý chạy gộp nhiều script test cùng lúc. | `python3 test/run_test_suite.py --suite quick` |

---

## 2. Phím tắt chạy Test Suite

| Mục tiêu | Câu lệnh |
|---|---|
| **Kiểm tra nhanh** | `python3 test/run_test_suite.py --suite quick` |
| **Test toàn bộ** (bỏ qua các script nặng) | `python3 test/run_test_suite.py --suite full` |
| **Test tất cả** (bao gồm cả benchmark nặng) | `python3 test/run_test_suite.py --suite full --include-heavy` |
| **Chỉ chạy script chỉ định** | `python3 test/run_test_suite.py --only ocr,owner_distribution,owner_remap` |
| **Chế độ nghiêm ngặt** (dừng ngay nếu có lỗi) | `python3 test/run_test_suite.py --suite quick --strict` |

---

## 3. Lưu ý quan trọng

* **Yêu cầu Server:** Các script `test_api_smoke.py` và `benchmark_stream_latency.py` yêu cầu Backend Django phải đang chạy.
* **URL mặc định:** Hầu hết script trỏ về `http://127.0.0.1:8000/api`.
* **Script nặng (Heavy):** `test_chunk_strategy.py`, `benchmark_retrieval_latency.py`, và `test_ragas_pipeline.py` sẽ tốn tài nguyên và thời gian vì phải gọi LLM/Embedding liên tục.
* **Dữ liệu đánh giá:** File chuẩn thường nằm ở `backend/evaluation_set.json`.

> **Mẹo nhỏ:** Trước khi deploy, nên chạy `suite quick` để đảm bảo không có lỗi ngớ ngẩn (broken code) nào xảy ra nhé!