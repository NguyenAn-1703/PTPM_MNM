"""
RAG Engine Module
Core logic cho Retrieval-Augmented Generation
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from django.conf import settings
from langchain_core.embeddings import Embeddings


class OllamaHTTPEmbeddings(Embeddings):
    """Minimal embedding client compatible with LangChain FAISS interface."""

    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts,
        }

        # Prefer modern Ollama endpoint that accepts batch input.
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings
        except Exception:
            pass

        # Fallback to legacy single-input endpoint for compatibility.
        vectors: List[List[float]] = []
        for text in texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            vector = data.get("embedding")
            if not vector:
                raise RuntimeError("Ollama embedding response missing 'embedding'")
            vectors.append(vector)

        return vectors

    def embed_query(self, text: str) -> List[float]:
        vectors = self.embed_documents([text])
        if not vectors:
            raise RuntimeError("Failed to generate query embedding")
        return vectors[0]


class RAGEngine:
    """
    RAG Engine class xử lý:
    - Text chunking
    - Vector storage với FAISS
    - Similarity search
    - LLM generation với Ollama
    """
    
    def __init__(self):
        self.vector_store_path = Path(settings.VECTOR_DB_PATH)
        self.ollama_base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        self.llm_model = settings.OLLAMA_LLM or "qwen2.5:7b"
        self.embedding_model = settings.EMBEDDING_MODEL or "nomic-embed-text"
        self.request_timeout = 120
        # FAISS returns L2 distance (lower is better). Distances above this threshold
        # are treated as irrelevant to avoid hallucinated answers.
        self.max_retrieval_distance = 1.2
        
        # Initialize embeddings
        self.embeddings = OllamaHTTPEmbeddings(
            base_url=self.ollama_base_url,
            model=self.embedding_model,
            timeout=self.request_timeout,
        )
        
        # Lightweight chunking configuration.
        self.chunk_size = 1000
        self.chunk_overlap = 150
        
        # Vector store
        self.vector_store: Optional[Any] = None
        self._load_vector_store()

        # Prompt configuration
        self.system_prompt = (
            "Bạn là trợ lý AI trả lời dựa trên ngữ cảnh được cung cấp."
            "Tuyệt đối không được tự ý thêm thông tin ngoài ngữ cảnh."
            "Hãy trả lời chính xác dựa trên thông tin đã cho."
            "Nếu không có đủ thông tin trong ngữ cảnh, phải trả lời đúng câu: "
            "'Không tìm thấy thông tin liên quan trong tài liệu đã upload.'."
        )
        self.history_max_messages = 7
        self.history_max_chars = 2000

    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks without importing heavy NLP stacks."""
        text = (text or "").strip()
        if not text:
            return []

        size = max(1, int(self.chunk_size))
        overlap = max(0, int(self.chunk_overlap))
        if overlap >= size:
            overlap = max(0, size // 5)

        step = max(1, size - overlap)
        chunks: List[str] = []

        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start += step

        return chunks

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format and truncate recent chat history."""
        if not history:
            return "Không có lịch sử hội thoại."

        filtered = []
        for item in history:
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                filtered.append({"role": role, "content": content})

        if not filtered:
            return "Không có lịch sử hội thoại."

        recent = filtered[-self.history_max_messages :]

        lines = []
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")

        history_text = "\n".join(lines)
        if len(history_text) > self.history_max_chars:
            history_text = history_text[-self.history_max_chars :]
            history_text = "..." + history_text

        return history_text

    def _condense_question(self, history: List[Dict[str, str]], question: str) -> str:
        """Rewrite the question into a standalone query using recent history."""
        if not history:
            return question

        history_text = self._format_history(history)

        condense_prompt = (
            "Dựa vào lịch sử hội thoại và câu hỏi mới nhất, "
            "hãy viết lại câu hỏi mới thành một câu hỏi độc lập, đầy đủ ý nghĩa. "
            "Chỉ trả về câu hỏi độc lập, không giải thích.\n\n"
            f"LỊCH SỬ HOI THOẠI:\n{history_text}\n\n"
            f"CÂU HỎI HIỆN TẠI: {question}\n\n"
            "CÂU HỎI ĐÔC LẬP:"
        )

        try:
            condensed = self._invoke_llm(condense_prompt)
            condensed = str(condensed).strip().strip('"')
            return condensed or question
        except Exception:
            return question

    def _invoke_llm(self, prompt: str) -> str:
        """Call Ollama generate API without importing heavyweight LangChain LLM wrappers."""
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()

    def _filter_relevant_contexts(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep only contexts with acceptable FAISS distance."""
        filtered = []
        for ctx in contexts:
            try:
                score = float(ctx.get("score", 0.0))
            except (TypeError, ValueError):
                continue

            if score <= self.max_retrieval_distance:
                filtered.append(ctx)

        return filtered
    
    def _load_vector_store(self):
        """Load vector store từ disk nếu tồn tại"""
        try:
            index_path = self.vector_store_path / "index.faiss"
            if index_path.exists():
                from langchain_community.vectorstores import FAISS

                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"✅ Loaded vector store from {self.vector_store_path}")
        except Exception as e:
            print(f"⚠️ Could not load vector store: {e}")
            self.vector_store = None
    
    def _save_vector_store(self):
        """Save vector store xuống disk"""
        if self.vector_store:
            self.vector_store_path.mkdir(parents=True, exist_ok=True)
            self.vector_store.save_local(str(self.vector_store_path))
            print(f"✅ Saved vector store to {self.vector_store_path}")
    
    def add_documents(self, text: str, metadata: Dict[str, Any] = None) -> int:
        """
        Thêm tài liệu vào vector store
        
        Args:
            text: Nội dung text của tài liệu
            metadata: Metadata bổ sung (tên file, loại file, etc.)
        
        Returns:
            Số lượng chunks đã thêm
        """
        if not text.strip():
            raise ValueError("Text rỗng, không thể thêm vào vector store")
        
        # Split text thành chunks
        chunks = self._split_text(text)
        
        logger.info(f"Processing {len(chunks)} chunks")
        
        if not chunks:
            raise ValueError("Không thể chia text thành chunks")
        
        # Tạo metadata cho mỗi chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(metadata or {})
            }
            metadatas.append(chunk_metadata)
        
        # Thêm vào vector store
        if self.vector_store is None:
            from langchain_community.vectorstores import FAISS

            self.vector_store = FAISS.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                metadatas=metadatas
            )
        else:
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=metadatas
            )
        
        # Save to disk
        self._save_vector_store()
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các chunks liên quan nhất đến query
        
        Args:
            query: Câu hỏi/truy vấn
            top_k: Số lượng kết quả trả về
        
        Returns:
            Danh sách các chunks với score
        """
        if self.vector_store is None:
            return []
        
        results = self.vector_store.similarity_search_with_score(query, k=top_k)
        
        search_results = []
        for doc, score in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        
        return search_results
    
    def chat(self, question: str, history: Optional[List[Dict[str, str]]] = None, top_k: int = 3) -> Dict[str, Any]:
        """
        Chat với RAG - trả lời câu hỏi dựa trên tài liệu đã upload
        
        Args:
            question: Câu hỏi của người dùng
            top_k: Số lượng context chunks sử dụng
        
        Returns:
            Dict chứa answer và retrieved contexts
        """
        if self.vector_store is None:
            return {
                "answer": "Chưa có tài liệu nào được upload. Vui lòng upload tài liệu trước khi đặt câu hỏi.",
                "contexts": [],
                "has_context": False
            }

        history = history or []
        standalone_question = self._condense_question(history, question)
        
        logger.info(f"Query: {question}")
        
        # Retrieve contexts and filter weak matches.
        contexts = self.search(standalone_question, top_k=top_k)
        contexts = self._filter_relevant_contexts(contexts)
        
        logger.info(f"Retrieved {len(contexts)} documents")
        
        if not contexts:
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu đã upload.",
                "contexts": [],
                "has_context": False
            }
        
        # Build context string
        context_text = "\n\n---\n\n".join([ctx["content"] for ctx in contexts])
        
        # Create prompt
        history_text = self._format_history(history)
        prompt = (
            f"SYSTEM PROMPT:\n{self.system_prompt}\n\n"
            f"CHAT HISTORY (3-5 câu gần nhất):\n{history_text}\n\n"
            f"RAG CONTEXT (chunks liên quan):\n{context_text}\n\n"
            f"CÂU HỎI HIỆN TẠI:\n{question}\n\n"
            "TRẢ LỜI:"
        )
        
        # Generate answer
        try:
            answer = self._invoke_llm(prompt)
        except Exception as e:
            answer = f"Lỗi khi gọi LLM: {str(e)}"
        
        return {
            "answer": answer,
            "contexts": contexts,
            "has_context": True
        }
    
    def clear_vector_store(self):
        """Xóa toàn bộ vector store"""
        self.vector_store = None
        
        # Xóa files trên disk
        if self.vector_store_path.exists():
            import shutil
            shutil.rmtree(self.vector_store_path)
        
        print("✅ Cleared vector store")
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê về vector store"""
        stats = {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "vector_db": "FAISS",
            "ollama_url": self.ollama_base_url,
            "history_max_messages": self.history_max_messages,
            "has_documents": self.vector_store is not None,
            "document_count": 0,
            "uploaded_files": []
        }
        
        if self.vector_store:
            try:
                stats["document_count"] = self.vector_store.index.ntotal
            except:
                pass

            try:
                # Deduplicate filenames stored in chunk metadata
                filenames = set()
                for doc in self.vector_store.docstore._dict.values():
                    filename = doc.metadata.get("filename")
                    if filename:
                        filenames.add(filename)
                stats["uploaded_files"] = sorted(filenames)
            except:
                pass
        
        return stats


# Singleton instance
_rag_engine: Optional[RAGEngine] = None

def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
