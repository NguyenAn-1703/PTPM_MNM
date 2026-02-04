## 1. Setup
```bash
python3 -m venv venv
source venv/bin/activate

```

## 2. Cài đặt 
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Tải model Ollama
```bash
# Tải model LLM  (Qwen 2.5 7B hoặc DeepSeek-R1)
ollama pull qwen2.5:7b

# Tải model chuyên dụng để Embedding (Nên dùng nomic-embed-text cho nhẹ và nhanh)
ollama pull nomic-embed-text
```
## 4. Khởi tạo Project Django
```bash
django-admin startproject rag_project .
python manage.py startapp api

```

## 5. Chạy Backend
```bash
python manage.py migrate
python manage.py runserver


# python manage.py makemigrations api 
```

## 6. API
```bash
 Endpoint	    Method	        Mô tả
/api/upload/	POST	        Upload file PDF/Word/Image
/api/chat/	    POST	        Chat với RAG
/api/status/	GET	            Kiểm tra trạng thái
/api/clear/	    DELETE	        Xóa vector store
```