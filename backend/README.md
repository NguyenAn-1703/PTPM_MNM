## 1. Tổng quan (Overview)

| Mục | Mô tả ngắn |
|---|---|
| Tech stack | Django, DRF, FAISS, Ollama, Tesseract OCR |
| Vai trò | Upload tài liệu, tạo index vector, chat theo ngữ cảnh RAG |
| Đường dẫn API | `http://localhost:8000/api` |
| Vector backend | Mặc định `faiss`, hỗ trợ `qdrant` migration |

> **Note thực tế:** Nếu chạy Docker, nhớ map port Ollama (11434) để Backend container gọi được model.

## 2. Cấu trúc chính (Architecture)



| Thư mục/File | Vai trò |
|---|---|
| `src/api/views.py` | API handlers, validate input, map response |
| `src/api/urls.py` | Đăng ký 10 endpoint |
| `src/controllers/chat_controller.py` | Điều phối chat flow (chat, stream, clear memory) |
| `src/services/upload_service.py` | Xử lý upload/indexing qua service layer |
| `src/services/chat_service.py` | Gọi RAG engine cho chat và stream |
| `src/llm/engine.py` | RAGEngine orchestration |
| `src/llm/retrieval.py` | Retrieval vector/hybrid/rerank/multi-vector |
| `src/llm/storage.py` | Lưu FAISS và source_documents registry |

> **Pro-tip:** Chia Service và Controller riêng giúp logic RAG không bị dính chặt vào HTTP Request, sau này viết Unit Test hay chạy Cron job cực dễ.

## 3. API endpoints

| Method | Path | Mục đích | Ghi chú nhanh |
|---|---|---|---|
| POST | `/api/upload/` | Upload và index tài liệu | Hỗ trợ `files`, `chunk_size`, `chunk_overlap`, `session_id` |
| POST | `/api/chat/` | Chat non-stream | Trả về JSON một cục sau khi LLM xong việc |
| POST | `/api/chat/stream/` | Chat streaming SSE | Trả về từng token (chữ) kiểu ChatGPT |
| POST | `/api/chat/memory/clear/` | Xóa memory theo session | Xóa lịch sử chat của user hiện tại |
| DELETE | `/api/clear/` | Xóa vector store | **Cẩn thận:** Bay màu toàn bộ database vector |

## 4. Retrieval modes (Chế độ truy vấn)

* **`vector`**: Tìm theo ngữ nghĩa (Semantic), phù hợp hỏi ý chính.
* **`hybrid`**: Mix thêm Keyword search (BM25), cực tốt khi cần tìm chính xác mã lỗi, tên riêng, số hiệu.
* **`hybrid_rerank`**: Lấy kết quả Hybrid xong bắt một Model nhỏ (Reranker) sắp xếp lại lần nữa. **Chậm hơn tí nhưng chính xác nhất.**

## 5. Request fields hay dùng (Params cần nhớ)

| Field | Kiểu | Ghi chú |
|---|---|---|
| `session_id` | string | ID định danh người dùng/phiên chat. Dùng để cách ly dữ liệu. |
| `top_k` | int | Số lượng "mẩu" văn bản sẽ ném cho LLM đọc. Thường để 5-10. |
| `use_self_rag` | bool | Nếu bật, LLM sẽ tự kiểm tra xem nội dung tìm được có liên quan không, nếu rác nó sẽ không trả lời bậy. |

## 6. Biến môi trường quan trọng (Environment Variables)

* `OLLAMA_LLM`: `qwen2.5:7b` (Con này đang hot, tiếng Việt cực mượt).
* `SELF_RAG_CONFIDENCE_THRESHOLD`: `0.58` (Nếu điểm tin cậy thấp hơn mức này, hệ thống sẽ báo "Em không biết").

## 7. Setup nhanh (Quick Start)

```bash
# Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài thư viện & Migrate DB
pip install -r requirements.txt
python3 manage.py migrate

# Chạy server
python3 manage.py runserver 0.0.0.0:8000
```

## 8. Lưu ý vận hành (Operational Notes)

1.  **OCR**: Nếu upload file ảnh/PDF scan mà không ra chữ, check lại `tesseract` đã cài trên OS chưa.
2.  **Legacy Data**: Khi FE gọi API, luôn kèm `owner_session_ids = [session_id, "legacy"]` để user thấy được cả file cũ hệ thống đã index sẵn.
3.  **Performance**: FAISS lưu local nên tốc độ phản hồi nhanh, nhưng nếu scale lên nhiều server thì phải switch sang Qdrant.

---
>**Backend** này tập trung vào tính linh hoạt (Modular). Bạn có thể đổi Model hay VectorDB trong file `.env` mà không cần sửa code. 