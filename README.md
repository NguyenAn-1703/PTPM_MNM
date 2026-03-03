# RAG Assistant — AI-Powered Document Q&A System

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Backend** | Django, Django REST Framework |
| **AI Orchestration** | LangChain |
| **LLM Runtime** | Ollama (Qwen2.5:7B / DeepSeek-R1:7B) |
| **Vector Database** | FAISS (Facebook AI Similarity Search) |
| **Embeddings** | nomic-embed-text (via Ollama) |
| **Document Processing** | PyPDF, python-docx, pytesseract (OCR), Pillow |

---

## How It Works

```
Document Upload
      │
      ▼
┌──────────────────────┐
│  Document Processor   │  Extracts text from PDF / DOCX / Image (OCR)
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  Text Splitter        │  Splits into chunks (1000 chars, 150 overlap)
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  Embedding Model      │  Converts chunks into vector representations
│  (nomic-embed-text)   │
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  FAISS Vector Store   │  Stores and indexes all embeddings on disk
└──────────────────────┘


User Question
      │
      ▼
┌──────────────────────┐
│  Question Condenser   │  LLM rephrases question using chat history
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  Similarity Search    │  Retrieves top-3 most relevant chunks
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  LLM (Qwen2.5:7B)    │  Generates answer grounded in retrieved context
└──────────────────────┘
      │
      ▼
    Answer + Source References
```

---

## Project Structure

```
PTPM_MNM/
├── backend/
│   ├── api/
│   │   ├── utils/
│   │   │   ├── rag_engine.py          # Core RAG pipeline (LangChain + FAISS)
│   │   │   └── document_processor.py  # Multi-format text extraction + OCR
│   │   ├── views.py                   # REST API endpoints
│   │   └── urls.py
│   ├── rag_project/
│   │   └── settings.py
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    └── src/
        ├── components/
        │   ├── ChatInterface.tsx       # Chat UI with message history
        │   ├── FileUpload.tsx          # Drag-and-drop file upload
        │   └── Sidebar.tsx             # System status panel
        ├── services/
        │   └── api.ts                  # Typed REST API client
        └── App.tsx
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running

### 1. Clone the repository

```bash
git clone https://github.com/your-username/PTPM_MNM.git
cd PTPM_MNM
```

### 2. Pull Ollama Models

```bash
ollama pull qwen2.5:7b          # LLM for chat
ollama pull nomic-embed-text    # Embedding model

# Make sure Ollama is running
ollama serve
```

### 3. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env — set SECRET_KEY and confirm Ollama model names

# Run migrations and start server
python manage.py migrate
python manage.py runserver      # http://localhost:8000
```

### 4. Frontend Setup

```bash
cd frontend

npm install
npm run dev                     # http://localhost:5173
```

Open `http://localhost:5173` in your browser.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload and process a document |
| `POST` | `/api/chat/` | Ask a question with optional chat history |
| `GET` | `/api/status/` | Get system health and model info |
| `DELETE` | `/api/clear/` | Remove all stored documents and embeddings |




---

## Environment Variables

Copy `.env.example` to `.env` inside the `backend/` folder:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM=qwen2.5:7b
EMBEDDING_MODEL=nomic-embed-text
```

---

## Configuration Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OLLAMA_LLM` | `qwen2.5:7b` | LLM model used for answer generation |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model for generating vector embeddings |
| Chunk size | 1000 chars | Size of each document chunk for indexing |
| Chunk overlap | 150 chars | Overlap between adjacent chunks |
| Top-K retrieval | 3 | Number of chunks returned per query |
| Max chat history | 7 messages | Context window for conversation memory |

---

## Supported File Formats

| Format | Processing |
|--------|-----------|
| `.pdf` | Text extraction via PyPDF |
| `.docx` / `.doc` | Parsed with python-docx |
| `.png`, `.jpg`, `.jpeg` | OCR via pytesseract |
| `.bmp`, `.tiff` | OCR via pytesseract |

---

## License

 See [LICENSE](LICENSE) for details.

---

