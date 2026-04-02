# Backend - RAG (Retrieval-Augmented Generation) System

> Hệ thống RAG backend sử dụng Django REST Framework, LangChain, FAISS, và Ollama để xây dựng chatbot hỏi đáp dựa trên tài liệu.

---

## 📋 Mục lục

1. [Tổng quan dự án](#-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
3. [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
4. [Luồng hoạt động](#-luồng-hoạt-động)
5. [API Endpoints](#-api-endpoints)
6. [Cài đặt và chạy](#-cài-đặt-và-chạy)
7. [Cấu hình môi trường](#-cấu-hình-môi-trường)
8. [Testing và Utilities](#-testing-và-utilities)

---

## 🎯 Tổng quan dự án

Backend này là một hệ thống RAG (Retrieval-Augmented Generation) hoàn chỉnh cho phép:

- **Upload tài liệu**: Hỗ trợ PDF, DOCX, DOC, PNG, JPG, TIFF với OCR tiếng Việt
- **Tự động indexing**: Chuyển đổi văn bản thành vector embeddings và lưu vào FAISS
- **Hỏi đáp thông minh**: Tìm kiếm context liên quan và sinh câu trả lời bằng LLM
- **Quản lý session**: Lưu lịch sử hội thoại với TTL tự động
- **Retrieval modes**: Vector search, keyword search, hybrid search với reranking
- **Self-RAG**: Tự đánh giá câu trả lời và tự động truy vấn lại nếu cần

---

## 🏗️ Kiến trúc hệ thống

### Layers

```
┌─────────────────────────────────────────────────┐
│         API Layer (Django REST Framework)        │
│  api/views.py - 8 endpoints (upload, chat, ...)  │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│          Business Logic (RAGEngine)             │
│  src/rag/engine.py - 6 Mixins orchestration     │
│  - Chat Pipeline  - Retrieval  - Self-RAG       │
│  - Indexing       - Memory     - Evaluation     │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│       Data Access & Infrastructure              │
│  - FAISS (vector store)                         │
│  - Ollama (LLM + Embeddings)                    │
│  - Tesseract (OCR)                              │
│  - SessionMemoryStore (in-memory with TTL)      │
└─────────────────────────────────────────────────┘
```

### Design Patterns

- **Singleton**: RAGEngine, Embeddings, LLMClient được cache toàn cục
- **Mixin**: Chia nhỏ chức năng thành 6 mixins (RAGChatPipelineMixin, RAGRetrievalMixin, ...)
- **Factory**: `get_embeddings()`, `get_llm_client()`, `get_storage()`
- **Layered Architecture**: API → Business Logic → Data Access

---

## 📁 Cấu trúc thư mục

```text
backend/
├── api/                          # Django REST Framework Layer
│   ├── views.py                  # 8 API endpoints (upload, chat, status, ...)
│   ├── urls.py                   # URL routing
│   └── models.py                 # (trống - dùng singleton pattern)
│
├── src/                          # Core Business Logic (Django-independent)
│   ├── config.py                 # RAGSettings dataclass - tập trung cấu hình
│   ├── database.py               # RagStorage bootstrap
│   ├── model_factory.py          # Singleton factories (Embeddings, LLM)
│   │
│   ├── ingestion/                # Document Processing
│   │   └── document_processor.py # Xử lý 6 loại file (PDF, DOCX, Images + OCR)
│   │
│   └── rag/                      # RAG Engine Core (Mixin Architecture)
│       ├── engine.py             # RAGEngine - Orchestrator chính
│       ├── runtime.py            # get_rag_engine() singleton
│       ├── chat_pipeline.py      # Conversational flow
│       ├── retrieval.py          # Vector/keyword/hybrid search + reranking
│       ├── memory.py             # TTL-based session management
│       ├── embeddings.py         # OllamaHTTPEmbeddings client
│       ├── prompts.py            # Vietnamese prompt templates
│       ├── storage.py            # FAISS persistence (RagStorage)
│       ├── self_rag.py           # Query rewrite & self-evaluation
│       ├── text.py               # Text splitting với char offsets
│       └── evaluation.py         # Chunk strategy testing
│
├── rag_project/                  # Django Project Settings
│   ├── settings.py               # Django + RAG configuration
│   ├── urls.py                   # Root URL routing
│   ├── wsgi.py                   # Production WSGI entry
│   └── asgi.py                   # ASGI entry
│
├── vector_db/                    # FAISS Persistence (local storage)
│   ├── index.faiss               # FAISS vector index
│   ├── docstore.pkl              # LangChain document store
│   ├── index_to_docstore_id.json # Index mapping
│   └── source_documents.json     # Original text + metadata registry
│
├── data/                         # Data directories
│   ├── raw/                      # Documents for batch ingestion
│   └── processed/                # Processed output
│
├── test_ocr.py                   # OCR testing utility
├── test_chunk_strategy.py        # Chunk strategy evaluator
├── main.py                       # Batch ingestion script
├── manage.py                     # Django management
└── requirements.txt              # Python dependencies
```

### Vai trò các thành phần chính

| Thành phần | Vai trò |
|-----------|--------|
| **api/views.py** | REST API endpoints - giao diện với client |
| **src/config.py** | Centralized config loader từ .env + Django settings |
| **src/ingestion/document_processor.py** | Extract text từ PDF (PyPDF), DOCX (python-docx), OCR (Tesseract) |
| **src/rag/engine.py** | Orchestrator - kết hợp 6 mixin, quản lý lifecycle |
| **src/rag/chat_pipeline.py** | LLM conversation + context retrieval flow |
| **src/rag/retrieval.py** | Vector search (FAISS), keyword (TF-IDF), hybrid (RRF) |
| **src/rag/memory.py** | In-memory session store với TTL eviction |
| **src/rag/embeddings.py** | HTTP client cho Ollama embedding API |
| **src/rag/storage.py** | FAISS persistence + source document registry |
| **vector_db/** | Persistent FAISS index + source registry |

---

## 🔄 Luồng hoạt động

### 1️⃣ Upload Document Flow (POST /api/upload/)

```
Client Request (multipart/form-data)
    ↓
UploadDocumentView
    ├─ Validate file extension (PDF, DOCX, PNG, JPG, TIFF)
    ├─ Create temp file
    ↓
DocumentProcessor
    ├─ PDF → PyPDF (extract text + page metadata)
    ├─ DOCX → python-docx (paragraphs + tables)
    ├─ Image → Tesseract OCR (Vietnamese + English)
    ↓
RAGIndexingMixin.add_documents()
    ├─ Normalize chunk_size, chunk_overlap
    ├─ Split text into chunks (with char offsets)
    ├─ Build metadata (filename, page_number, char_start/end)
    ↓
OllamaHTTPEmbeddings
    ├─ POST /api/embed (batch embedding)
    ↓
FAISS Vector Store
    ├─ Index vectors
    ├─ Store documents
    ├─ Save to disk (index.faiss + docstore.pkl)
    ↓
RagStorage.save_source_documents()
    └─ Lưu original text + metadata để re-index với tham số khác
```

**Đặc điểm:**
- ✅ Multi-file upload support
- ✅ Configurable chunk_size/overlap per request
- ✅ Page-level tracking cho PDF (page_number metadata)
- ✅ Character offset tracking (char_start, char_end)
- ✅ OCR fallback: vie+eng → eng nếu Vietnamese không khả dụng

---

### 2️⃣ Chat Flow (POST /api/chat/)

**Input Example:**
```json
{
  "question": "Hợp đồng này có thời hạn bao lâu?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "session_id": "user123",
  "retrieval_mode": "hybrid",
  "filenames": ["contract.pdf"],
  "use_reranker": true,
  "use_self_rag": true
}
```

**12-Step Pipeline:**

1. **Session Normalization**
   - `normalize_session_id()` → UUID nếu empty
   - `sanitize_history()` → Chỉ giữ user/assistant messages
   - Load effective history từ client hoặc in-memory store

2. **Question Condensing**
   - LLM call: "Viết lại câu hỏi độc lập từ history"
   - Prompt: `build_condense_question_prompt(history, question)`
   - Detect `rewritten = (condensed != original)`

3. **Retrieval Mode Selection**
   
   **Vector Search:**
   ```
   FAISS.similarity_search_with_score(question, k=max(6, top_k*2))
   ↓
   Filter by max_retrieval_distance (1.2)
   ↓
   Filter by metadata (filenames, file_types)
   ```
   
   **Hybrid Search (Default):**
   ```
   vector_candidates = FAISS vector search
   keyword_candidates = TF-IDF keyword search
       ├─ TF-IDF: score = freq(token) * log(total_docs / docs_with_token)
   ↓
   Fuse RRF: score = 1/(k+rank_vector) + 1/(k+rank_keyword)
       └─ k=60 (fusion parameter)
   ```

4. **Optional Reranking**
   ```
   if use_reranker:
     ├─ CrossEncoder (nếu ENABLE_CROSS_ENCODER=true)
     ├─ Pairs: [[query, context_text], ...]
     └─ Fallback: lexical overlap (term intersection)
   ```

5. **Check Context Availability**
   - Nếu không tìm thấy context → Return "Không tìm thấy..." (no LLM call)

6. **Build Answer Prompt**
   ```
   SYSTEM_PROMPT 
   + CHAT_HISTORY (last 7 messages) 
   + RAG_CONTEXT (top-k chunks) 
   + CURRENT_QUESTION
   ```

7. **LLM Generation**
   - `OllamaLLMClient.generate(prompt, temperature=0.2)`
   - POST `http://localhost:11434/api/generate`

8. **Self-Evaluation** (nếu use_self_rag=true)
   ```
   _self_evaluate_answer(question, answer, contexts)
   ├─ Prompt: JSON output {"supported": bool, "confidence": 0-1}
   ├─ Parse JSON response
  └─ if confidence < SELF_RAG_CONFIDENCE_THRESHOLD → Trigger Self-RAG
   ```

9. **Self-RAG Retrieval** (nếu confidence thấp)
   ```
   _rewrite_query_for_retrieval(question, history)
   ↓
   Re-retrieve với rewritten query
   ↓
   Re-rerank + Re-generate answer
   ↓
   Compare confidence → Giữ câu trả lời tốt hơn
   ```

10. **Confidence Scoring**
    ```
    score = 0.6 * self_eval_confidence
          + 0.4 * (1 if has_context else 0)
          - 0.15 * (1 if no_context else 0)
    
    Label:
    - >= 0.75 → "high"
    - >= 0.45 → "medium"
    - else    → "low"
    ```

11. **Build Citations**
    - Highlight context references trong answer
    - Format: [1], [2], [3]

12. **Save to Memory & Return**
    - Append {user_msg, assistant_msg} to session
    - Return full response với metadata

**Output Example:**
```json
{
  "success": true,
  "answer": "Hợp đồng có thời hạn 12 tháng...",
  "contexts": [
    {
      "content": "Điều 3: Thời hạn hợp đồng là 12 tháng...",
      "metadata": {
        "filename": "contract.pdf",
        "page_number": 2,
        "char_start": 150,
        "char_end": 350
      },
      "score": 0.15
    }
  ],
  "has_context": true,
  "session_id": "user123",
  "standalone_question": "Hợp đồng có thời hạn bao lâu?",
  "rewritten": false,
  "retrieval_mode": "hybrid",
  "reranker": {
    "used": true,
    "model": "cross-encoder/ms-marco-MiniLM-L-6-v2"
  },
  "self_rag_applied": false,
  "confidence_score": 0.78,
  "confidence_label": "high",
  "self_check": {
    "supported": true,
    "confidence": 0.75,
    "feedback": "Câu trả lời được hỗ trợ bởi context"
  }
}
```

---

### 3️⃣ Memory/Conversation Handling

**SessionMemoryStore Configuration:**
- `history_max_messages`: 7 (giữ tối đa 14 messages = 7 cặp user-assistant)
- `max_memory_sessions`: 200 (max concurrent sessions)
- `session_ttl_seconds`: 21600 (6 hours expiration)
- Thread-safe với locks

**Key Methods:**
1. `normalize_session_id()` → UUID hoặc clean string (max 64 chars)
2. `sanitize_history()` → Filter + bounded size
3. `get_session_history()` → Lock + evict expired + return
4. `append_session_messages()` → Add + evict overflow
5. `_evict_stale_sessions()` → Remove old/overflow sessions

---

## 📡 API Endpoints

### 1. Upload Document
**POST** `/api/upload/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/upload/ \
  -F "files=@contract.pdf" \
  -F "files=@invoice.docx" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=150"
```

**Response:**
```json
{
  "success": true,
  "message": "Uploaded 2 documents",
  "files": [
    {"filename": "contract.pdf", "chunks": 15},
    {"filename": "invoice.docx", "chunks": 8}
  ]
}
```

---

### 2. Chat
**POST** `/api/chat/`

**Request:**
```json
{
  "question": "Hợp đồng này có thời hạn bao lâu?",
  "history": [],
  "session_id": "user123",
  "retrieval_mode": "hybrid",
  "top_k": 5,
  "filenames": ["contract.pdf"],
  "use_reranker": true,
  "use_self_rag": true
}
```

**Parameters:**
- `retrieval_mode`: "vector" | "hybrid" | "hybrid_multivector" (default: hybrid)
- `top_k`: Số lượng context chunks (default: 5)
- `filenames`: Filter theo tên file cụ thể
- `file_types`: Filter theo loại file
- `page_from`, `page_to`: Filter theo trang
- `uploaded_after`, `uploaded_before`: Filter theo thời gian upload (ISO8601)
- `tags`: Filter theo nhãn metadata
- `use_reranker`: Enable cross-encoder reranking
- `use_self_rag`: Enable self-evaluation và auto-requery

---

### 3. Chat Streaming (SSE)
**POST** `/api/chat/stream/`

Trả về `text/event-stream` với các event:
- `meta`: thông tin trace, retrieval mode, reranker và timing retrieve/rerank
- `token`: token từ Ollama theo thời gian thực
- `done`: payload cuối cùng (answer, contexts, confidence, self_check)
- `error`: lỗi trong pipeline streaming

**Response:** (xem ví dụ ở phần Chat Flow)

---

### 4. Clear Session Memory
**POST** `/api/chat/memory/clear/`

```json
{
  "session_id": "user123"
}
```

---

### 5. System Status
**GET** `/api/status/`

**Response:**
```json
{
  "success": true,
  "ollama_available": true,
  "embedding_model": "nomic-embed-text",
  "llm_model": "deepseek-r1:7b",
  "vector_store_stats": {
    "total_documents": 150,
    "unique_filenames": 12,
    "storage_path": "./vector_db"
  }
}
```

---

### 6. Clear Vector Store
**DELETE** `/api/clear/`

---

### 7. Delete Document
**DELETE** `/api/documents/delete/`

```json
{
  "filename": "contract.pdf"
}
```

---

### 8. Evaluate Chunk Strategy
**POST** `/api/chunk-strategy/evaluate/`

Đánh giá các tổ hợp chunk size/overlap với bộ câu hỏi.

```bash
python test_chunk_strategy.py --evaluation-file evaluation_set.json
```

---

### 9. Retrieval Benchmark
**POST** `/api/retrieval/benchmark/`

So sánh retrieval modes (vector, hybrid, hybrid_rerank, hybrid_multivector).

---

### 10. Self-RAG Threshold Calibration
**POST** `/api/self-rag/calibrate/`

Calibrate ngưỡng `SELF_RAG_CONFIDENCE_THRESHOLD` từ benchmark set:

```json
{
  "evaluation_set": [
    {
      "question": "...",
      "expected_keywords": ["..."],
      "expected_answer": "..."
    }
  ],
  "top_k": 3,
  "retrieval_mode": "hybrid",
  "run_ragas": false,
  "persist_artifact": true
}
```

- `run_ragas=true`: chạy thêm metric RAGAS (faithfulness/answer_relevancy/context_precision) nếu đã cài dependencies.
- `persist_artifact=true`: lưu artifact versioned tại `CALIBRATION_ARTIFACT_DIR`.

---

## 🚀 Cài đặt và chạy

### Prerequisites

**1. Python 3.9+**

**2. Tesseract OCR**
```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng

# Windows
# Download: https://github.com/UB-Mannheim/tesseract/wiki
# Install to: C:\Program Files\Tesseract-OCR
```

**3. Ollama (LLM + Embeddings)**
```bash
# Download và install: https://ollama.ai
ollama serve &
ollama pull deepseek-r1:7b
ollama pull nomic-embed-text
```

---

### Setup Steps

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Upgrade pip và install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env với settings của bạn

# 5. Database migration
python3 manage.py migrate

# 6. Run development server
python3 manage.py runserver 0.0.0.0:8000
```

**Server will start at:** `http://localhost:8000`

---

### Production Deployment

```bash
# Install Gunicorn
pip install gunicorn

# Run với 4 workers
gunicorn -w 4 -b 0.0.0.0:8000 rag_project.wsgi:application
```

---

## ⚙️ Cấu hình môi trường

### File: `.env`

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM=deepseek-r1:7b
EMBEDDING_MODEL=nomic-embed-text

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
CHUNKING_STRATEGY=recursive

# Retrieval & Context
ENABLE_MULTI_VECTOR=true
ENABLE_CONTEXT_REORDER=true
ENABLE_CONTEXT_COMPRESSION=true
CONTEXT_CANDIDATE_POOL=12
CONTEXT_DEDUPE_JACCARD_THRESHOLD=0.82
CONTEXT_COMPRESSION_MAX_CHARS=900

# Self-RAG
SELF_RAG_CONFIDENCE_THRESHOLD=0.58

# Vector backend migration
VECTOR_BACKEND=faiss
ENABLE_QDRANT_DUAL_WRITE=false
ENABLE_QDRANT_SHADOW_READ=false
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=rag_chunks

# Calibration artifacts
ENABLE_RAGAS_IN_CALIBRATION=false
PERSIST_CALIBRATION_ARTIFACTS=true
CALIBRATION_ARTIFACT_DIR=./artifacts/self_rag

# Storage
VECTOR_DB_PATH=./vector_db

# OCR (Windows only)
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

### Advanced Settings (settings.py)

```python
# Cross-Encoder Reranking
ENABLE_CROSS_ENCODER = True
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Logging
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'level': 'INFO'}
    },
    'loggers': {
        'django': {'level': 'INFO'},
        'src': {'level': 'INFO'}
    }
}
```

### Configuration Table

| Biến | Mặc định | Vai trò |
|------|----------|---------|
| **OLLAMA_BASE_URL** | http://localhost:11434 | URL Ollama server |
| **OLLAMA_LLM** | deepseek-r1:7b | Model LLM chat |
| **EMBEDDING_MODEL** | nomic-embed-text | Model embedding |
| **CHUNK_SIZE** | 1000 | Độ dài chunk mặc định |
| **CHUNK_OVERLAP** | 150 | Độ chồng lấn chunk |
| **CHUNKING_STRATEGY** | recursive | Chiến lược chunking: fixed/recursive/semantic |
| **ENABLE_MULTI_VECTOR** | true | Bật indexing content + summary + hypothetical query |
| **ENABLE_CONTEXT_REORDER** | true | Chống Lost-in-the-Middle bằng context reordering |
| **ENABLE_CONTEXT_COMPRESSION** | true | Bật nén context trước khi generate |
| **CONTEXT_CANDIDATE_POOL** | 12 | Số lượng candidate context trước rerank |
| **CONTEXT_DEDUPE_JACCARD_THRESHOLD** | 0.82 | Ngưỡng loại bỏ context trùng lặp |
| **CONTEXT_COMPRESSION_MAX_CHARS** | 900 | Giới hạn ký tự context sau nén |
| **SELF_RAG_CONFIDENCE_THRESHOLD** | 0.58 | Ngưỡng kích hoạt Self-RAG retry |
| **VECTOR_BACKEND** | faiss | Backend retrieval chính: faiss hoặc qdrant |
| **ENABLE_QDRANT_DUAL_WRITE** | false | Ghi song song sang Qdrant khi vẫn đọc từ FAISS |
| **ENABLE_QDRANT_SHADOW_READ** | false | Đọc shadow từ Qdrant để so kết quả, chưa cutover |
| **QDRANT_URL** | http://localhost:6333 | URL Qdrant service |
| **QDRANT_COLLECTION** | rag_chunks | Collection Qdrant dùng cho chunk vectors |
| **ENABLE_RAGAS_IN_CALIBRATION** | false | Bật chạy metric RAGAS khi calibrate threshold |
| **PERSIST_CALIBRATION_ARTIFACTS** | true | Lưu artifact calibrate versioned |
| **CALIBRATION_ARTIFACT_DIR** | ./artifacts/self_rag | Thư mục artifact calibrate |
| **VECTOR_DB_PATH** | ./vector_db | Thư mục lưu FAISS |
| **SESSION_TTL** | 21600 (6h) | Thời gian sống session |
| **MAX_SESSIONS** | 200 | Max concurrent sessions |
| **HISTORY_MAX_MESSAGES** | 7 | Max pairs user-assistant |
| **MAX_RETRIEVAL_DISTANCE** | 1.2 | FAISS similarity threshold |
| **ENABLE_CROSS_ENCODER** | True | Bật cross-encoder reranking |

---

## 🧪 Testing và Utilities

### 1. Test OCR
```bash
python test_ocr.py
```
Kiểm tra Tesseract OCR với Vietnamese + English.

---

### 2. Evaluate Chunk Strategy
```bash
python test_chunk_strategy.py --evaluation-file evaluation_set.json
```

**evaluation_set.json format:**
```json
{
  "questions": [
    {
      "question": "Hợp đồng có thời hạn bao lâu?",
      "expected_answer": "12 tháng",
      "relevant_documents": ["contract.pdf"]
    }
  ]
}
```

Đánh giá các tổ hợp:
- chunk_size: 500, 1000, 1500
- chunk_overlap: 50, 100, 150, 200

---

## 📦 Dependencies

### Core Packages
| Package | Purpose |
|---------|---------|
| **django** | Web framework |
| **djangorestframework** | REST API |
| **django-cors-headers** | CORS handling |
| **langchain** | RAG framework |
| **langchain-community** | Community integrations |
| **langchain-text-splitters** | Recursive text chunking |
| **faiss-cpu** | Vector similarity search |
| **qdrant-client** | Optional Qdrant backend migration |
| **pypdf** | PDF text extraction |
| **python-docx** | DOCX processing |
| **pytesseract** | OCR wrapper |
| **Pillow** | Image processing |
| **sentence-transformers** | Cross-encoder reranking |
| **ragas** | Optional calibration quality metrics |
| **datasets** | Dataset format for RAGAS |
| **python-dotenv** | Environment variables |
| **requests** | HTTP client |

---

## 🔍 Performance Notes

| Metric | Value | Notes |
|--------|-------|-------|
| **Chunk Size** | 1000 | Configurable per request |
| **Chunk Overlap** | 150 | Configurable per request |
| **Session TTL** | 6 hours | Auto-evict sau khi hết hạn |
| **Max Sessions** | 200 | Drop oldest nếu overflow |
| **Max History** | 14 messages | 7 cặp user-assistant |
| **LLM Temperature** | 0.2 | Deterministic responses |
| **LLM Timeout** | 120s | Request timeout |
| **Retrieval Distance** | 1.2 | FAISS similarity threshold |
| **RRF Fusion K** | 60 | Hybrid search parameter |

---

## 📚 Quick Reference

### Main Entry Points
- **API**: `api/views.py` (8 view classes)
- **Engine**: `src/rag/engine.py` (RAGEngine)
- **Runtime**: `src/rag/runtime.py` (get_rag_engine singleton)

### Database
- **Django**: SQLite (`db.sqlite3`)
- **Vector**: FAISS (`vector_db/`)

### Logs
- Django: `INFO` logging (toggle trong settings.py)
- Level: `WARNING` by default (change to `INFO` để bật chi tiết)

---

