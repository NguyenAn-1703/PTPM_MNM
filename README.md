# RAG Assistant — AI-Powered Document Q&A System

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running
- Tesseract OCR installed (for image uploads)


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

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Backend** | Django, Django REST Framework |
| **AI Orchestration** | LangChain |
| **LLM** | Ollama (Qwen2.5:7B) |
| **Vector Database** | FAISS (Facebook AI Similarity Search) |
| **Embeddings** | nomic-embed-text (via Ollama) |
| **Document Processing** | PyPDF, python-docx, pytesseract (OCR), Pillow |

---

## How It Works

![RAG Process Architecture](img/RAG.png)
---

## [LICENSE](LICENSE)


