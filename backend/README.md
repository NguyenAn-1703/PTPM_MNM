## 1. Setup
```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

```

## 2. Cài đặt 
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Cài Tesseract OCR (bắt buộc cho upload ảnh)
Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
```

## 4. Tải model Ollama
```bash
# Tải model LLM (tùy chọn, có thể dùng qwen2.5:7b hoặc deepseek-r1:7b)
ollama pull qwen2.5:7b

# Tải model chuyên dụng để Embedding (Nên dùng nomic-embed-text cho nhẹ và nhanh)
ollama pull nomic-embed-text
```
<!-- ## 5. Khởi tạo Project Django
```bash
django-admin startproject rag_project .
python manage.py startapp api

``` -->

## 5. Chạy Backend
```bash
python manage.py migrate
python manage.py runserver

# python manage.py makemigrations api 
```

## 7. API
```bash
 Endpoint	    Method	        Mô tả
/api/upload/	POST	        Upload 1 hoặc nhiều file PDF/Word/Image
/api/chat/	    POST	        Chat với RAG
/api/chat/memory/clear/	POST	Reset memory theo session_id
/api/status/	GET	            Kiểm tra trạng thái
/api/clear/	    DELETE	        Xóa vector store
/api/chunk-strategy/evaluate/	POST	Đánh giá các tổ hợp chunk_size/chunk_overlap
/api/retrieval/benchmark/	POST	So sánh vector vs hybrid vs hybrid_rerank
```

## Cấu trúc backend theo hướng RAG

```text
backend/
├── data/
│   ├── raw/                 # Tài liệu thô để nạp chỉ mục
│   └── processed/           # Dữ liệu đã chuẩn hóa (tùy chọn)
├── vector_db/               # FAISS index + source registry
├── src/
│   ├── ingestion/           # Loader + document processor (PDF/DOCX/OCR)
│   ├── rag/                 # Engine, retrieval, indexing, memory, prompts
│   ├── config.py            # Cấu hình runtime tập trung
│   ├── database.py          # Khởi tạo storage/vector db
│   ├── model_factory.py     # Khởi tạo embeddings + LLM client
│   └── utils.py             # Helper tiện ích
├── api/                     # DRF endpoint layer (views + urls)
├── rag_project/             # Django settings/urls/wsgi
├── app.py                   # Script snapshot trạng thái backend
├── main.py                  # Script nạp dữ liệu từ data/raw vào vector_db
└── manage.py
```

Runtime hiện chỉ dùng `vector_db` làm nơi lưu chỉ mục.

`POST /api/chat/` hiện trả về `contexts[]` kèm citation/source tracking:

- `source_location.page_start/page_end`: số trang nguồn (nếu là PDF)
- `source_location.char_start/char_end`: vị trí ký tự trong tài liệu gốc
- `highlights[]`: các đoạn văn trong context được dùng để tạo câu trả lời

`POST /api/chat/` hỗ trợ nâng cao cho Hybrid RAG + Rerank + Self-RAG:

- Request body bổ sung:
	- `retrieval_mode`: `"vector"` hoặc `"hybrid"` (mặc định `hybrid`)
	- `filenames`: mảng tên file để metadata filtering theo tài liệu
	- `file_types`: mảng loại file (`pdf`, `docx`, ...)
	- `use_reranker`: bật/tắt cross-encoder reranking
	- `use_self_rag`: bật/tắt self-evaluation + query rewrite vòng 2
- Response bổ sung:
	- `confidence_score`: điểm tin cậy 0..1
	- `confidence_label`: `low | medium | high`
	- `retrieval_mode`, `applied_filters`, `reranker`, `self_rag_applied`, `self_check`

Lưu ý reranker:

- Mặc định hệ thống dùng fallback lexical để tránh tải model nặng trong môi trường dev.
- Để bật cross-encoder thật, thêm `ENABLE_CROSS_ENCODER=true` trong môi trường backend.

`POST /api/chat/` hỗ trợ conversational memory theo phiên hội thoại:

- Request body:
	- `question` (string, bắt buộc)
	- `history` (array optional, gồm các item `{ role: "user" | "assistant", content: string }`)
	- `session_id` (string optional, nên gửi theo từng cuộc hội thoại để backend theo dõi ngữ cảnh)
- Response bổ sung:
	- `session_id`: id phiên backend đã dùng để lưu memory
	- `standalone_question`: câu hỏi follow-up đã được chuẩn hóa thành câu hỏi độc lập trước khi retrieve
	- `rewritten`: `true/false`, cho biết câu hỏi hiện tại có được rewrite từ follow-up hay không

Ví dụ:

```bash
curl -X POST http://localhost:8000/api/chat/ \
	-H "Content-Type: application/json" \
	-d '{
		"question": "Còn phần deadline thì sao?",
		"retrieval_mode": "hybrid",
		"filenames": ["project-plan.pdf"],
		"use_reranker": true,
		"use_self_rag": true,
		"session_id": "chat-1711960000",
		"history": [
			{"role": "user", "content": "Tóm tắt mục tiêu dự án"},
			{"role": "assistant", "content": "..."}
		]
	}'
```

Reset memory theo session:

```bash
curl -X POST http://localhost:8000/api/chat/memory/clear/ \
	-H "Content-Type: application/json" \
	-d '{"session_id": "chat-1711960000"}'
```

## 8. Upload với chunk parameters tùy chỉnh

`POST /api/upload/` hỗ trợ thêm 2 field form-data:

- `chunk_size` (int > 0)
- `chunk_overlap` (int >= 0, phải nhỏ hơn `chunk_size`)

Đồng thời hỗ trợ upload nhiều file trong 1 request bằng field `files` lặp lại nhiều lần.

Ví dụ:

```bash
curl -X POST http://localhost:8000/api/upload/ \
	-F "files=@/path/to/document-1.pdf" \
	-F "files=@/path/to/document-2.docx" \
	-F "chunk_size=1500" \
	-F "chunk_overlap=200"
```

## 9. Benchmark chunk strategy và xuất report accuracy

Tạo file `evaluation_set.json`:

```json
[
	{
		"question": "Tài liệu nói gì về mục tiêu dự án?",
		"expected_keywords": ["mục tiêu", "dự án"]
	},
	{
		"question": "Mô hình LLM đang được dùng là gì?",
		"expected_keywords": ["qwen", "ollama"]
	}
]
```

Chạy script benchmark với 12 tổ hợp mặc định:

```bash
python test_chunk_strategy.py --evaluation-file evaluation_set.json
```

Script sẽ thử:

- `chunk_size`: `500, 1000, 1500, 2000`
- `chunk_overlap`: `50, 100, 200`

và xuất:

- Bảng so sánh `retrieval_accuracy` trên terminal
- File JSON report (mặc định: `chunk_strategy_report.json`)

## 10. Benchmark retrieval mode (vector vs hybrid vs hybrid_rerank)

`POST /api/retrieval/benchmark/` hỗ trợ báo cáo định lượng theo mode truy xuất:

- `vector`
- `hybrid`
- `hybrid_rerank`

Input:

- `evaluation_set`: danh sách `{ question, expected_keywords[] }`
- `retrieval_modes` (optional): danh sách mode cần so sánh
- `top_k` (optional)
- `filenames`, `file_types` (optional): metadata filtering

Output:

- `retrieval_accuracy`, `hits/total_questions`
- `avg_latency_ms`
- `details[]` theo từng câu hỏi

Ví dụ:

```bash
curl -X POST http://localhost:8000/api/retrieval/benchmark/ \
	-H "Content-Type: application/json" \
	-d '{
		"evaluation_set": [
			{"question": "Mục tiêu dự án là gì?", "expected_keywords": ["mục tiêu", "dự án"]},
			{"question": "Mô hình nào đang dùng?", "expected_keywords": ["qwen", "ollama"]}
		],
		"retrieval_modes": ["vector", "hybrid", "hybrid_rerank"],
		"top_k": 3
	}'
```