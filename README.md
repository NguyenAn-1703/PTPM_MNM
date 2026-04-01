<div align="center">

# RAG Assistant - AI-Powered Document Q&A System

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Ollama](https://img.shields.io/badge/Ollama-White?style=for-the-badge&logo=ollama&logoColor=black)](https://ollama.ai/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)

</div>

---

## Giới thiệu dự án

> **RAG Assistant** là một hệ thống hỏi đáp và phân tích tài liệu thông minh (Q&A System), vận hành dựa trên sức mạnh của AI và kiến trúc **RAG (Retrieval-Augmented Generation)**.

Dự án tập trung vào các tính năng cốt lõi:

- Giao diện UI/UX trực quan, hiện đại, tối ưu trải nghiệm với **React 19, TypeScript** và **Tailwind CSS**.
- Hệ thống hỗ trợ phong phú định dạng tài liệu: **PDF, Word (DOCX/DOC)**, phân tích và trích xuất cả thông tin văn bản từ hình ảnh (OCR) thông qua `pytesseract`.
- Cấu trúc Backend linh hoạt xây dựng trên **Django** & **Django REST Framework**.
- Tìm kiếm vector ngữ nghĩa siêu tốc độ với **FAISS** và mô hình nhúng `nomic-embed-text`.
- Trả lời nhanh chóng, chính xác nhờ mô hình ngôn ngữ lớn **Qwen2.5 (7B)** tích hợp local thông qua sức mạnh từ **Ollama** và **LangChain**.

---

<div align="center">

![RAG Process Architecture](./docs/RAG.png) <!-- Kiến trúc xử lý luồng hệ thống RAG -->

</div>

---

## Kiến trúc hệ thống

Dự án được phân tách cấu trúc rõ ràng giữa frontend và backend thuận tiện cho việc nâng cấp & mở rộng:

```text
RAG_Assistant/
├── backend/                    # Core Django Backend
│   ├── api/                    # Xử lý Logic & APIs
│   ├── rag_project/            # Cấu hình dự án Django
│   ├── vector_store/           # Nơi lưu trữ vector FAISS database
│   ├── requirements.txt        # Các gói thư viện phụ thuộc
│   └── manage.py               # Khởi chạy hệ thống server
│
├── frontend/                   # UI/UX với React + TypeScript
│   ├── src/                    # Mã nguồn giao diện chính
│   └── package.json            # Thư viện Frontend (Node.js)
│
├── img/                        # Hình ảnh mô phỏng kiến trúc
│   └── RAG.png                 # Sơ đồ khối hoạt động (Architecture Process)
└── README.md                   # Thông tin đầy đủ dự án
```

---

## Cấu hình hệ thống linh hoạt

Hệ thống cho phép điều chỉnh các tham số cấu hình nhanh chóng giúp tối ưu quá trình vận hành & truy xuất:

| Tham số cấu hình | Giá trị mặc định | Diễn giải chức năng |
|-----------|---------|-------------|
| `OLLAMA_LLM` | `qwen2.5:7b` | LLM dùng để tự động thiết lập câu trả lời |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Mô hình vector hóa thông tin dữ liệu thô |
| Chunk size | 1000 chars (mặc định, có thể tùy chỉnh khi upload) | Kích thước khi chia nhỏ định trang văn bản tải lên |
| Chunk overlap | 150 chars (mặc định, có thể tùy chỉnh khi upload) | Khoảng đệm giữ lại giữa các chunk liên tiếp |
| Top-K retrieval | 3 | Trả về 3 ngữ cảnh chính xác nhất hỗ trợ câu hỏi |
| Max chat history | 7 messages | Bộ nhớ Contextual hạn chế ghi nhớ lịch sử cuộc hội thoại |

API đánh giá chunk strategy hỗ trợ benchmark các tổ hợp `chunk_size/chunk_overlap` và trả report `retrieval_accuracy` tại endpoint `POST /api/chunk-strategy/evaluate/`.

---

## Hướng dẫn cài đặt

#### 1. Yêu cầu hệ thống (Prerequisites)

- **Python 3.10+** (để khởi chạy Backend và bộ RAG AI)
- **Node.js 18+** (cho nền tảng vận hành Frontend)
- [Ollama](https://ollama.ai) đã cài đặt, phục vụ local (`qwen2.5:7b`, `nomic-embed-text`)
- Phần mềm **Tesseract OCR** đã thiết lập vào Environment Variables

#### 2. Clone repository

```bash
git clone https://github.com/NguyenAn-1703/PTPM_MNM.git
cd PTPM_MNM
```

#### 3. Sử dụng & Cài đặt môi trường Backend

```bash
cd backend

python -m venv venv
# Đối với Windows:
venv\Scripts\activate
# Đối với MacOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Khởi chạy ứng dụng server local:
python manage.py runserver
```

#### 4. Sử dụng & Cài đặt giao diện Frontend

```bash
cd frontend

npm install

npm run dev
```
---

<div align="center">
⭐ Nếu bạn thích dự án này, hãy cho nó một star nhé!
</div>
