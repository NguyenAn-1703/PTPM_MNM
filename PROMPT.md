
 cấu trúc **C.R.E.A.T.E** (Context, Role, Explicit Action, Task, Evaluation) 

---

### Xây dựng Hệ thống Đa phương thức RAG (Django + Ollama + React/Tailwind)
> **Context:** Tôi là một sinh viên năm cuối ngành Công nghệ Thông tin, đang thực hiện đồ án tốt nghiệp về hệ thống Retrieval-Augmented Generation (RAG) sử dụng mô hình ngôn ngữ lớn (LLM) chạy cục bộ. Mục tiêu của ông là xây dựng một ứng dụng web cho phép người dùng tải lên các tài liệu đa phương thức (PDF, Word, Ảnh) để AI có thể đọc hiểu và trả lời câu hỏi dựa trên nội dung đó.

> **Role:** Bạn là một Full-stack Senior Developer và AI Engineer chuyên về hệ thống Retrieval-Augmented Generation (RAG).

> **Task:** Hãy xây dựng một ứng dụng Web hoàn chỉnh hỗ trợ người dùng upload đa phương thức tài liệu (PDF, Word, Ảnh) để AI đọc hiểu và trả lời câu hỏi dựa trên nội dung đó.
> **Tech Stack yêu cầu:**
> 1. **Backend:** Python, Django, Django REST Framework.
> 2. **AI Framework:** LangChain.
> 3. **LLM & Embedding:** deepseek-r1:7b (via Ollama) và model embedding `paraphrase-multilingual-mpnet-base-v2` (hoặc `nomic-embed-text`).
> 4. **Vector Database:** FAISS hoặc ChromaDB.
> 5. **Frontend:** React.js kết hợp với Tailwind CSS.
> 
> 
> **Yêu cầu chi tiết về chức năng:**
> **1. Data Ingestion (Backend):**
> * Viết module xử lý đa định dạng:
> * **PDF:** Dùng `PyPDF` hoặc `PyMuPDF`.
> * **Word:** Dùng `python-docx`.
> * **Image (OCR):** Dùng `pytesseract` để trích xuất chữ từ file PNG/JPG.
> 
> 
> * **Chunking:** Sử dụng `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=150).
> * **Vector Storage:** Chuyển đổi text thành vector và lưu trữ cục bộ để truy vấn nhanh.
> 
> 
> **2. RAG Logic (Backend):**
> * Xây dựng API `/api/upload/` để nhận file và xử lý vào Vector DB.
> * Xây dựng API `/api/chat/` để nhận câu hỏi:
> * Thực hiện Search tương đồng (Similarity Search) để lấy Top-3 context liên quan nhất.
> * Gửi Context + Question vào Prompt cho model deepseek-r1:7b để trả kết quả.
> 
> 
> 
> 
> **3. Giao diện (Frontend):**
> * Thiết kế UI giống trong ảnh đính kèm:
> * Bên trái: Sidebar hiển thị thông số (Model: deepseek-r1:7b, Vector DB: FAISS, Embedding Model).
> * Bên phải: Khu vực Upload file và khung chat (Chat Interface) trực quan.
> * Có phần "View Retrieved Context" để người dùng kiểm tra AI lấy thông tin từ đâu.
> 
> 
> 
> 
> **4. Cấu trúc Project:**
> * Tổ chức folder chuẩn Django: `api/`, `models/`, `views/`, `utils/` (xử lý RAG).
> * Viết file `requirements.txt` đầy đủ.
> 
> 
> **Output:** Hãy viết code chi tiết cho các file quan trọng nhất (như `utils.py` xử lý RAG và `views.py` xử lý API) và hướng dẫn cách kết nối Frontend - Backend.

---
