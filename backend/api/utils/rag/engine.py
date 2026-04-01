"""RAG engine orchestration layer."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from .embeddings import OllamaHTTPEmbeddings
from .memory import SessionMemoryStore
from .storage import RagStorage
from .text import build_citations, format_history, normalize_chunk_params, split_text, split_text_with_offsets


logger = logging.getLogger(__name__)


class RAGEngine:
    """Core RAG orchestration: indexing, retrieval, and answer generation."""

    def __init__(self):
        self.vector_store_path = Path(settings.VECTOR_DB_PATH)
        self.ollama_base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        self.llm_model = settings.OLLAMA_LLM or "qwen2.5:7b"
        self.embedding_model = settings.EMBEDDING_MODEL or "nomic-embed-text"
        self.request_timeout = 120
        # FAISS returns L2 distance (lower is better). Distances above this threshold
        # are treated as irrelevant to avoid hallucinated answers.
        self.max_retrieval_distance = 1.2

        self.embeddings = OllamaHTTPEmbeddings(
            base_url=self.ollama_base_url,
            model=self.embedding_model,
            timeout=self.request_timeout,
        )

        self.chunk_size = 1000
        self.chunk_overlap = 150

        self.storage = RagStorage(self.vector_store_path)
        self.vector_store: Optional[Any] = self.storage.load_vector_store(self.embeddings)

        self.system_prompt = (
            "Bạn là trợ lý AI trả lời dựa trên ngữ cảnh được cung cấp."
            "Tuyệt đối không được tự ý thêm thông tin ngoài ngữ cảnh."
            "Hãy trả lời chính xác dựa trên thông tin đã cho."
            "Nếu không có đủ thông tin trong ngữ cảnh, phải trả lời đúng câu: "
            "'Không tìm thấy thông tin liên quan trong tài liệu đã upload.'."
        )
        self.history_max_messages = 7
        self.history_max_chars = 2000

        self.memory = SessionMemoryStore(
            history_max_messages=self.history_max_messages,
            max_memory_sessions=200,
            session_ttl_seconds=6 * 60 * 60,
        )

    @property
    def session_ttl_seconds(self) -> int:
        return self.memory.session_ttl_seconds

    def clear_session_memory(self, session_id: str) -> bool:
        return self.memory.clear_session_memory(session_id)

    def _invoke_llm(self, prompt: str) -> str:
        """Call Ollama generate API without heavyweight wrappers."""
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

    def _condense_question(self, history: List[Dict[str, str]], question: str) -> str:
        """Rewrite the question into a standalone query using recent history."""
        if not history:
            return question

        history_text = format_history(
            history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )

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

    def add_documents(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        source_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Add one extracted document into FAISS index."""
        if not text.strip():
            raise ValueError("Text rỗng, không thể thêm vào vector store")

        normalized_chunk_size, normalized_chunk_overlap = normalize_chunk_params(
            default_size=self.chunk_size,
            default_overlap=self.chunk_overlap,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        if source_segments:
            for segment in source_segments:
                segment_text = str(segment.get("text", "")).strip()
                if not segment_text:
                    continue

                segment_start = int(segment.get("char_start", 0))
                segment_page = segment.get("page_number")

                segment_chunks = split_text_with_offsets(
                    segment_text,
                    chunk_size=normalized_chunk_size,
                    chunk_overlap=normalized_chunk_overlap,
                    base_offset=segment_start,
                )

                for seg_chunk in segment_chunks:
                    chunks.append(seg_chunk["content"])
                    metadatas.append(
                        {
                            "chunk_size": normalized_chunk_size,
                            "chunk_overlap": normalized_chunk_overlap,
                            "page_number": segment_page,
                            "char_start": seg_chunk["char_start"],
                            "char_end": seg_chunk["char_end"],
                            **(metadata or {}),
                        }
                    )
        else:
            fallback_chunks = split_text_with_offsets(
                text,
                chunk_size=normalized_chunk_size,
                chunk_overlap=normalized_chunk_overlap,
                base_offset=0,
            )

            for fallback_chunk in fallback_chunks:
                chunks.append(fallback_chunk["content"])
                metadatas.append(
                    {
                        "chunk_size": normalized_chunk_size,
                        "chunk_overlap": normalized_chunk_overlap,
                        "char_start": fallback_chunk["char_start"],
                        "char_end": fallback_chunk["char_end"],
                        **(metadata or {}),
                    }
                )

        logger.info("Processing %s chunks", len(chunks))

        if not chunks:
            raise ValueError("Không thể chia text thành chunks")

        for i in range(len(chunks)):
            metadatas[i] = {
                **metadatas[i],
                "chunk_index": i,
                "total_chunks": len(chunks),
            }

        if self.vector_store is None:
            from langchain_community.vectorstores import FAISS

            self.vector_store = FAISS.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                metadatas=metadatas,
            )
        else:
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=metadatas,
            )

        self.storage.save_vector_store(self.vector_store)
        self.storage.persist_source_document(
            text=text,
            metadata={
                "chunk_size": normalized_chunk_size,
                "chunk_overlap": normalized_chunk_overlap,
                **(metadata or {}),
            },
        )

        return len(chunks)

    def _build_temp_vector_store(self, source_docs: List[Dict[str, Any]], chunk_size: int, chunk_overlap: int):
        """Create an isolated FAISS vector store for a chunk configuration."""
        from langchain_community.vectorstores import FAISS

        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc_idx, doc in enumerate(source_docs):
            source_text = str(doc.get("text", "")).strip()
            if not source_text:
                continue

            base_metadata = doc.get("metadata", {}) or {}
            chunks = split_text(source_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for chunk_idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append(
                    {
                        "source_doc_index": doc_idx,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap,
                        **base_metadata,
                    }
                )

        if not texts:
            return None, 0

        temp_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
        )
        return temp_store, len(texts)

    def evaluate_chunk_strategy(
        self,
        evaluation_set: List[Dict[str, Any]],
        chunk_sizes: List[int],
        chunk_overlaps: List[int],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Evaluate chunk configurations and return retrieval accuracy report."""
        if not evaluation_set:
            raise ValueError("evaluation_set không được rỗng")

        source_docs = self.storage.load_source_documents()
        if not source_docs:
            raise ValueError("Không có source documents để đánh giá. Hãy upload tài liệu trước.")

        valid_cases: List[Dict[str, Any]] = []
        for idx, case in enumerate(evaluation_set):
            question = str(case.get("question", "")).strip()
            if not question:
                raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")

            expected_keywords = case.get("expected_keywords") or []
            if not isinstance(expected_keywords, list):
                raise ValueError(f"evaluation_set[{idx}].expected_keywords phải là list")

            cleaned_keywords = [str(item).strip().lower() for item in expected_keywords if str(item).strip()]
            valid_cases.append(
                {
                    "question": question,
                    "expected_keywords": cleaned_keywords,
                }
            )

        reports: List[Dict[str, Any]] = []
        for size in chunk_sizes:
            for overlap in chunk_overlaps:
                normalized_size, normalized_overlap = normalize_chunk_params(
                    default_size=self.chunk_size,
                    default_overlap=self.chunk_overlap,
                    chunk_size=size,
                    chunk_overlap=overlap,
                )
                temp_store, generated_chunks = self._build_temp_vector_store(
                    source_docs=source_docs,
                    chunk_size=normalized_size,
                    chunk_overlap=normalized_overlap,
                )

                if temp_store is None:
                    continue

                hit_count = 0
                per_question: List[Dict[str, Any]] = []

                for case in valid_cases:
                    results = temp_store.similarity_search_with_score(case["question"], k=top_k)
                    contexts: List[Dict[str, Any]] = []
                    for doc, score in results:
                        contexts.append(
                            {
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "score": float(score),
                            }
                        )

                    contexts = self._filter_relevant_contexts(contexts)
                    joined_context = "\n".join([item["content"] for item in contexts]).lower()
                    expected_keywords = case["expected_keywords"]

                    if expected_keywords:
                        is_hit = all(keyword in joined_context for keyword in expected_keywords)
                    else:
                        is_hit = len(contexts) > 0

                    if is_hit:
                        hit_count += 1

                    per_question.append(
                        {
                            "question": case["question"],
                            "expected_keywords": expected_keywords,
                            "retrieved_contexts": len(contexts),
                            "hit": is_hit,
                        }
                    )

                total = len(valid_cases)
                accuracy = round(hit_count / total, 4) if total else 0.0

                reports.append(
                    {
                        "chunk_size": normalized_size,
                        "chunk_overlap": normalized_overlap,
                        "retrieval_accuracy": accuracy,
                        "hits": hit_count,
                        "total_questions": total,
                        "generated_chunks": generated_chunks,
                        "details": per_question,
                    }
                )

        sorted_reports = sorted(
            reports,
            key=lambda item: (item["retrieval_accuracy"], -item["generated_chunks"]),
            reverse=True,
        )

        return {
            "summary": {
                "source_documents": len(source_docs),
                "evaluated_configs": len(sorted_reports),
                "metric": "retrieval_accuracy",
            },
            "best_config": sorted_reports[0] if sorted_reports else None,
            "reports": sorted_reports,
        }

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top-k candidate chunks from FAISS."""
        if self.vector_store is None:
            return []

        results = self.vector_store.similarity_search_with_score(query, k=top_k)

        search_results = []
        for doc, score in results:
            search_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                }
            )

        return search_results

    def chat(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 3,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Answer user question based on uploaded documents with retrieval context."""
        if self.vector_store is None:
            return {
                "answer": "Chưa có tài liệu nào được upload. Vui lòng upload tài liệu trước khi đặt câu hỏi.",
                "contexts": [],
                "has_context": False,
            }

        resolved_session_id = self.memory.normalize_session_id(session_id)
        client_history = self.memory.sanitize_history(history or [])
        memory_history = self.memory.get_session_history(resolved_session_id)
        effective_history = client_history if client_history else memory_history

        if client_history:
            self.memory.set_session_history(resolved_session_id, client_history)

        standalone_question = self._condense_question(effective_history, question)
        rewritten = standalone_question.strip().lower() != question.strip().lower()

        logger.info("Query: %s", question)

        contexts = self.search(standalone_question, top_k=top_k)
        contexts = self._filter_relevant_contexts(contexts)

        logger.info("Retrieved %s documents", len(contexts))

        if not contexts:
            self.memory.append_session_messages(
                resolved_session_id,
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": "Không tìm thấy thông tin liên quan trong tài liệu đã upload."},
                ],
            )
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu đã upload.",
                "contexts": [],
                "has_context": False,
                "session_id": resolved_session_id,
                "standalone_question": standalone_question,
                "rewritten": rewritten,
            }

        context_text = "\n\n---\n\n".join([ctx["content"] for ctx in contexts])
        history_text = format_history(
            effective_history,
            history_max_messages=self.history_max_messages,
            history_max_chars=self.history_max_chars,
        )
        prompt = (
            f"SYSTEM PROMPT:\n{self.system_prompt}\n\n"
            f"CHAT HISTORY (3-5 câu gần nhất):\n{history_text}\n\n"
            f"RAG CONTEXT (chunks liên quan):\n{context_text}\n\n"
            f"CÂU HỎI HIỆN TẠI:\n{question}\n\n"
            "TRẢ LỜI:"
        )

        try:
            answer = self._invoke_llm(prompt)
        except Exception as exc:
            answer = f"Lỗi khi gọi LLM: {str(exc)}"

        self.memory.append_session_messages(
            resolved_session_id,
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )

        return {
            "answer": answer,
            "contexts": build_citations(contexts, answer),
            "has_context": True,
            "session_id": resolved_session_id,
            "standalone_question": standalone_question,
            "rewritten": rewritten,
        }

    def clear_vector_store(self):
        """Clear in-memory and on-disk vector store."""
        self.vector_store = None
        self.storage.clear_vector_store()

    def get_stats(self) -> Dict[str, Any]:
        """Collect current runtime and index statistics."""
        source_documents = self.storage.load_source_documents()
        stats = {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "vector_db": "FAISS",
            "ollama_url": self.ollama_base_url,
            "history_max_messages": self.history_max_messages,
            "memory_session_ttl_seconds": self.session_ttl_seconds,
            "default_chunk_size": self.chunk_size,
            "default_chunk_overlap": self.chunk_overlap,
            "has_documents": self.vector_store is not None,
            "document_count": 0,
            "uploaded_files": [],
            "source_document_count": len(source_documents),
            "active_memory_sessions": self.memory.active_sessions(),
        }

        if self.vector_store:
            try:
                stats["document_count"] = self.vector_store.index.ntotal
            except Exception:
                pass

            try:
                filenames = set()
                for doc in self.vector_store.docstore._dict.values():
                    filename = doc.metadata.get("filename")
                    if filename:
                        filenames.add(filename)
                stats["uploaded_files"] = sorted(filenames)
            except Exception:
                pass

        return stats
