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
/api/upload/	POST	        Upload file PDF/Word/Image
/api/chat/	    POST	        Chat với RAG
/api/status/	GET	            Kiểm tra trạng thái
/api/clear/	    DELETE	        Xóa vector store
/api/chunk-strategy/evaluate/	POST	Đánh giá các tổ hợp chunk_size/chunk_overlap
```

## 8. Upload với chunk parameters tùy chỉnh

`POST /api/upload/` hỗ trợ thêm 2 field form-data:

- `chunk_size` (int > 0)
- `chunk_overlap` (int >= 0, phải nhỏ hơn `chunk_size`)

Ví dụ:

```bash
curl -X POST http://localhost:8000/api/upload/ \
	-F "file=@/path/to/document.pdf" \
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