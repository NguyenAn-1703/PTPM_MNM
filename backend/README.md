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
```