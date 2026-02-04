"""
RAG Engine Module
Core logic cho Retrieval-Augmented Generation
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from django.conf import settings

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama


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
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.llm_model = settings.OLLAMA_LLM
        self.embedding_model = settings.EMBEDDING_MODEL
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(
            model=self.embedding_model,
            base_url=self.ollama_base_url
        )
        
        # Initialize LLM
        self.llm = Ollama(
            model=self.llm_model,
            base_url=self.ollama_base_url,
            temperature=0.7
        )
        
        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Vector store
        self.vector_store: Optional[FAISS] = None
        self._load_vector_store()
    
    def _load_vector_store(self):
        """Load vector store từ disk nếu tồn tại"""
        try:
            index_path = self.vector_store_path / "index.faiss"
            if index_path.exists():
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
        chunks = self.text_splitter.split_text(text)
        
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
    
    def chat(self, question: str, top_k: int = 3) -> Dict[str, Any]:
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
        
        # Retrieve relevant contexts
        contexts = self.search(question, top_k=top_k)
        
        if not contexts:
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu đã upload.",
                "contexts": [],
                "has_context": False
            }
        
        # Build context string
        context_text = "\n\n---\n\n".join([ctx["content"] for ctx in contexts])
        
        # Create prompt
        prompt = f"""Bạn là một trợ lý AI thông minh. Hãy trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.
Nếu không tìm thấy thông tin trong ngữ cảnh, hãy nói rõ rằng bạn không tìm thấy thông tin liên quan.

NGỮCẢNH:
{context_text}

CÂU HỎI: {question}

TRẢ LỜI:"""
        
        # Generate answer
        try:
            answer = self.llm.invoke(prompt)
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
            "has_documents": self.vector_store is not None,
            "document_count": 0
        }
        
        if self.vector_store:
            try:
                stats["document_count"] = self.vector_store.index.ntotal
            except:
                pass
        
        return stats


# Singleton instance
_rag_engine: Optional[RAGEngine] = None

def get_rag_engine() -> RAGEngine:
    """Get singleton RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
