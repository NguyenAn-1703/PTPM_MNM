"""
API Views for RAG System
"""
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import List
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework import status
import uuid


logger = logging.getLogger(__name__)


class ServerSentEventRenderer(BaseRenderer):
    """Renderer to satisfy DRF content negotiation for SSE endpoints."""

    media_type = "text/event-stream"
    format = "sse"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        return str(data).encode("utf-8")


def _get_rag_engine():
    from src.llm.runtime import get_rag_engine
    return get_rag_engine()


def _parse_int(value, field_name: str, min_value: int = 0):
    if value in (None, ""):
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} phải là số nguyên")

    if parsed < min_value:
        raise ValueError(f"{field_name} phải >= {min_value}")

    return parsed


def _parse_bool(value, field_name: str):
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return True

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{field_name} phải là kiểu boolean")


def _parse_string_list(value) -> List[str]:
    if value in (None, ""):
        return []

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(value, list):
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    raise ValueError("Danh sách filter không hợp lệ")


def _parse_trace_id(request) -> str:
    trace_id = str(request.headers.get("X-Trace-Id") or request.data.get("trace_id") or "").strip()
    if not trace_id:
        return uuid.uuid4().hex
    if len(trace_id) > 128:
        return trace_id[:128]
    return trace_id


def _build_metadata_filters(request_data) -> dict:
    metadata_filters = {
        "filenames": _parse_string_list(request_data.get("filenames", [])),
        "file_types": _parse_string_list(request_data.get("file_types", [])),
        "tags": _parse_string_list(request_data.get("tags", [])),
        "uploaded_after": str(request_data.get("uploaded_after", "")).strip() or None,
        "uploaded_before": str(request_data.get("uploaded_before", "")).strip() or None,
    }

    page_from = _parse_int(request_data.get("page_from"), "page_from", min_value=1)
    page_to = _parse_int(request_data.get("page_to"), "page_to", min_value=1)
    if page_from is not None and page_to is not None and page_to < page_from:
        raise ValueError("page_to phải >= page_from")

    metadata_filters["page_from"] = page_from
    metadata_filters["page_to"] = page_to
    return metadata_filters


class UploadDocumentView(APIView):
    """
    API endpoint để upload tài liệu
    POST /api/upload/
    """
    parser_classes = [MultiPartParser, FormParser]
    
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'bmp', 'tiff']
    IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff']

    def _process_single_file(self, uploaded_file, chunk_size, chunk_overlap):
        from src.ingestion.document_processor import process_document, get_file_extension, extract_pdf_pages
        from src.ingestion.archive import persist_uploaded_artifacts

        filename = uploaded_file.name
        file_ext = get_file_extension(filename)

        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Định dạng file không hỗ trợ: {file_ext}. Chỉ hỗ trợ: {', '.join(self.ALLOWED_EXTENSIONS)}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            text = process_document(tmp_path, file_ext)
            source_segments = extract_pdf_pages(tmp_path) if file_ext == 'pdf' else None

            if not text.strip():
                error_message = "Không thể trích xuất text từ tài liệu. File có thể rỗng hoặc không có nội dung chữ."
                if file_ext in self.IMAGE_EXTENSIONS:
                    error_message = (
                        "OCR không trích xuất được text từ ảnh. "
                        "Kiểm tra ảnh có chữ rõ ràng và đảm bảo Tesseract + gói ngôn ngữ đã được cài đặt đúng."
                    )
                raise ValueError(error_message)

            artifact_info = {"raw_file": "", "processed_file": ""}
            try:
                artifact_info = persist_uploaded_artifacts(
                    tmp_path=tmp_path,
                    original_filename=filename,
                    extracted_text=text,
                )
            except Exception as exc:
                # Upload/index flow should continue even if archival write fails.
                logger.warning("Không thể lưu artifact vào data folder cho %s: %s", filename, exc)

            rag_engine = _get_rag_engine()
            uploaded_at = datetime.utcnow()
            metadata = {
                "filename": filename,
                "file_type": file_ext,
                "uploaded_at": uploaded_at.isoformat() + "Z",
                "uploaded_at_ts": uploaded_at.timestamp(),
            }
            if artifact_info.get("raw_file"):
                metadata["data_raw_file"] = artifact_info["raw_file"]
            if artifact_info.get("processed_file"):
                metadata["data_processed_file"] = artifact_info["processed_file"]

            chunks_added = rag_engine.add_documents(
                text=text,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                source_segments=source_segments,
            )

            return {
                "filename": filename,
                "file_type": file_ext,
                "text_length": len(text),
                "chunks_added": chunks_added,
                "data_raw_file": artifact_info.get("raw_file"),
                "data_processed_file": artifact_info.get("processed_file"),
            }
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    def post(self, request):
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files and 'file' in request.FILES:
            uploaded_files = [request.FILES['file']]

        if not uploaded_files:
            return Response(
                {"error": "Không tìm thấy file trong request"},
                status=status.HTTP_400_BAD_REQUEST
            )

        chunk_size_raw = request.data.get('chunk_size')
        chunk_overlap_raw = request.data.get('chunk_overlap')

        try:
            chunk_size = _parse_int(chunk_size_raw, 'chunk_size', min_value=1)
            chunk_overlap = _parse_int(chunk_overlap_raw, 'chunk_overlap', min_value=0)
            if chunk_size is not None and chunk_overlap is not None and chunk_overlap >= chunk_size:
                return Response(
                    {"error": "chunk_overlap phải nhỏ hơn chunk_size"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            processed_files = []
            total_chunks_added = 0
            total_text_length = 0

            for uploaded_file in uploaded_files:
                file_result = self._process_single_file(uploaded_file, chunk_size, chunk_overlap)
                processed_files.append(file_result)
                total_chunks_added += int(file_result["chunks_added"])
                total_text_length += int(file_result["text_length"])

            rag_engine = _get_rag_engine()

            if len(processed_files) == 1:
                only_file = processed_files[0]
                return Response({
                    "success": True,
                    "message": f"Đã xử lý thành công file: {only_file['filename']}",
                    "filename": only_file["filename"],
                    "file_type": only_file["file_type"],
                    "text_length": only_file["text_length"],
                    "chunks_added": only_file["chunks_added"],
                    "chunk_size": chunk_size or rag_engine.chunk_size,
                    "chunk_overlap": chunk_overlap or rag_engine.chunk_overlap,
                    "processed_files": processed_files,
                    "total_files": 1,
                    "total_chunks_added": total_chunks_added,
                })

            return Response({
                "success": True,
                "message": f"Đã xử lý thành công {len(processed_files)} file",
                "filename": processed_files[0]["filename"],
                "file_type": "multiple",
                "text_length": total_text_length,
                "chunks_added": total_chunks_added,
                "chunk_size": chunk_size or rag_engine.chunk_size,
                "chunk_overlap": chunk_overlap or rag_engine.chunk_overlap,
                "processed_files": processed_files,
                "total_files": len(processed_files),
                "total_chunks_added": total_chunks_added,
            })
            
        except Exception as e:
            return Response(
                {"error": f"Lỗi xử lý file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatView(APIView):
    """
    API endpoint để chat với RAG
    POST /api/chat/
    """
    parser_classes = [JSONParser]

    @staticmethod
    def _parse_history(history_raw):
        if history_raw in (None, ""):
            return []

        if not isinstance(history_raw, list):
            raise ValueError("history phải là danh sách")

        parsed = []
        for idx, item in enumerate(history_raw):
            if not isinstance(item, dict):
                raise ValueError(f"history[{idx}] không hợp lệ")

            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()

            if role not in {"user", "assistant"}:
                raise ValueError(f"history[{idx}].role phải là user hoặc assistant")
            if not content:
                raise ValueError(f"history[{idx}].content không được để trống")

            parsed.append({"role": role, "content": content})

        return parsed

    @staticmethod
    def _parse_session_id(session_id_raw):
        if session_id_raw in (None, ""):
            return None

        session_id = str(session_id_raw).strip()
        if len(session_id) > 128:
            raise ValueError("session_id không được dài quá 128 ký tự")

        return session_id
    
    def post(self, request):
        question = request.data.get('question', '').strip()
        history_raw = request.data.get('history', [])
        session_id_raw = request.data.get('session_id')
        retrieval_mode_raw = str(request.data.get('retrieval_mode', 'hybrid')).strip().lower()
        use_reranker_raw = request.data.get('use_reranker', True)
        use_self_rag_raw = request.data.get('use_self_rag', True)
        trace_id = _parse_trace_id(request)
        
        if not question:
            return Response(
                {"error": "Câu hỏi không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            history = self._parse_history(history_raw)
            session_id = self._parse_session_id(session_id_raw)
            use_reranker = _parse_bool(use_reranker_raw, 'use_reranker')
            use_self_rag = _parse_bool(use_self_rag_raw, 'use_self_rag')
            if retrieval_mode_raw not in {'vector', 'hybrid', 'hybrid_multivector'}:
                return Response(
                    {"error": "retrieval_mode phải là vector, hybrid hoặc hybrid_multivector"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            metadata_filters = _build_metadata_filters(request.data)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rag_engine = _get_rag_engine()
            result = rag_engine.chat(
                question,
                history=history,
                session_id=session_id,
                retrieval_mode=retrieval_mode_raw,
                metadata_filters=metadata_filters,
                use_reranker=use_reranker,
                use_self_rag=use_self_rag,
                trace_id=trace_id,
            )
            
            return Response({
                "success": True,
                "question": question,
                "answer": result["answer"],
                "contexts": result["contexts"],
                "has_context": result["has_context"],
                "session_id": result.get("session_id"),
                "standalone_question": result.get("standalone_question", question),
                "rewritten": bool(result.get("rewritten", False)),
                "retrieval_mode": result.get("retrieval_mode", retrieval_mode_raw),
                "applied_filters": result.get("applied_filters", metadata_filters),
                "reranker": result.get("reranker", {"used": False, "model": None}),
                "self_rag_applied": bool(result.get("self_rag_applied", False)),
                "confidence_score": result.get("confidence_score", 0.0),
                "confidence_label": result.get("confidence_label", "low"),
                "self_check": result.get("self_check", {}),
                "trace_id": result.get("trace_id", trace_id),
                "timings_ms": result.get("timings_ms", {}),
            })
            
        except Exception as e:
            return Response(
                {"error": f"Lỗi xử lý câu hỏi: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatStreamView(APIView):
    """
    API endpoint để chat streaming qua SSE
    POST /api/chat/stream/
    """

    parser_classes = [JSONParser]
    renderer_classes = [ServerSentEventRenderer, JSONRenderer]

    def post(self, request):
        question = str(request.data.get('question', '')).strip()
        if not question:
            return Response(
                {"error": "Câu hỏi không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            history = ChatView._parse_history(request.data.get('history', []))
            session_id = ChatView._parse_session_id(request.data.get('session_id'))
            retrieval_mode_raw = str(request.data.get('retrieval_mode', 'hybrid')).strip().lower()
            if retrieval_mode_raw not in {'vector', 'hybrid', 'hybrid_multivector'}:
                return Response(
                    {"error": "retrieval_mode phải là vector, hybrid hoặc hybrid_multivector"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            use_reranker = _parse_bool(request.data.get('use_reranker', True), 'use_reranker')
            use_self_rag = _parse_bool(request.data.get('use_self_rag', True), 'use_self_rag')
            metadata_filters = _build_metadata_filters(request.data)
            trace_id = _parse_trace_id(request)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        rag_engine = _get_rag_engine()

        def _event_stream():
            try:
                for event in rag_engine.chat_stream(
                    question=question,
                    history=history,
                    session_id=session_id,
                    retrieval_mode=retrieval_mode_raw,
                    metadata_filters=metadata_filters,
                    use_reranker=use_reranker,
                    use_self_rag=use_self_rag,
                    trace_id=trace_id,
                ):
                    event_name = str(event.get('event', 'message'))
                    data = event.get('data', {})
                    payload = json.dumps(data, ensure_ascii=False)
                    yield f"event: {event_name}\ndata: {payload}\n\n"
            except Exception as exc:
                payload = json.dumps({"error": str(exc), "trace_id": trace_id}, ensure_ascii=False)
                yield f"event: error\ndata: {payload}\n\n"

        response = StreamingHttpResponse(_event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class SelfRAGCalibrationView(APIView):
    """
    API endpoint calibrate ngưỡng Self-RAG từ benchmark set
    POST /api/self-rag/calibrate/
    """

    parser_classes = [JSONParser]

    def post(self, request):
        evaluation_set = request.data.get('evaluation_set', [])
        retrieval_mode = str(request.data.get('retrieval_mode', 'hybrid')).strip().lower()
        run_ragas_raw = request.data.get('run_ragas', False)
        persist_artifact_raw = request.data.get('persist_artifact', False)

        if not isinstance(evaluation_set, list) or not evaluation_set:
            return Response(
                {"error": "evaluation_set phải là danh sách và không được rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            top_k = _parse_int(request.data.get('top_k', 3), 'top_k', min_value=1)
            run_ragas = _parse_bool(run_ragas_raw, 'run_ragas')
            persist_artifact = _parse_bool(persist_artifact_raw, 'persist_artifact')
            if retrieval_mode not in {'vector', 'hybrid', 'hybrid_multivector'}:
                return Response(
                    {"error": "retrieval_mode phải là vector, hybrid hoặc hybrid_multivector"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        rag_engine = _get_rag_engine()
        try:
            original_multi_vector = bool(getattr(rag_engine, 'enable_multi_vector', False))
            if retrieval_mode == 'hybrid_multivector':
                rag_engine.enable_multi_vector = True

            try:
                report = rag_engine.calibrate_self_rag_threshold(
                    evaluation_set=evaluation_set,
                    top_k=top_k or 3,
                    retrieval_mode='hybrid' if retrieval_mode == 'hybrid_multivector' else retrieval_mode,
                    run_ragas=run_ragas,
                    persist_artifact=persist_artifact,
                )
            finally:
                rag_engine.enable_multi_vector = original_multi_vector

            return Response(
                {
                    "success": True,
                    "threshold": report.get("threshold"),
                    "metrics": report.get("metrics", {}),
                    "samples": report.get("samples", 0),
                    "rows": report.get("rows", []),
                    "ragas": report.get("ragas"),
                    "artifact_path": report.get("artifact_path"),
                }
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {"error": f"Lỗi calibrate self-rag: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClearSessionMemoryView(APIView):
    """
    API endpoint để xóa memory hội thoại theo session_id
    POST /api/chat/memory/clear/
    """

    parser_classes = [JSONParser]

    def post(self, request):
        session_id_raw = request.data.get('session_id')
        session_id = str(session_id_raw or '').strip()

        if not session_id:
            return Response(
                {"error": "session_id không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(session_id) > 128:
            return Response(
                {"error": "session_id không được dài quá 128 ký tự"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rag_engine = _get_rag_engine()
            cleared = rag_engine.clear_session_memory(session_id)
            return Response(
                {
                    "success": True,
                    "session_id": session_id,
                    "cleared": cleared,
                    "message": "Đã reset ngữ cảnh hội thoại cho session" if cleared else "Session chưa có memory để xóa",
                }
            )
        except Exception as e:
            return Response(
                {"error": f"Lỗi xóa memory hội thoại: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatusView(APIView):
    """
    API endpoint để kiểm tra trạng thái hệ thống
    GET /api/status/
    """
    def get(self, request):
        try:
            rag_engine = _get_rag_engine()
            stats = rag_engine.get_stats()
            
            return Response({
                "success": True,
                "status": "running",
                **stats
            })
        except Exception as e:
            return Response({
                "success": False,
                "status": "error",
                "error": str(e)
            })


class ClearVectorStoreView(APIView):
    """
    API endpoint để xóa vector store
    DELETE /api/clear/
    """
    def delete(self, request):
        try:
            rag_engine = _get_rag_engine()
            rag_engine.clear_vector_store()
            
            return Response({
                "success": True,
                "message": "Đã xóa toàn bộ dữ liệu vector store"
            })
        except Exception as e:
            return Response(
                {"error": f"Lỗi xóa vector store: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteDocumentByFilenameView(APIView):
    """
    API endpoint để xóa tài liệu theo filename
    DELETE /api/documents/delete/
    """

    parser_classes = [JSONParser]

    def delete(self, request):
        filename_raw = request.data.get('filename')
        filename = str(filename_raw or '').strip()

        if not filename:
            return Response(
                {"error": "filename không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(filename) > 255:
            return Response(
                {"error": "filename không được dài quá 255 ký tự"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rag_engine = _get_rag_engine()
            result = rag_engine.delete_documents_by_filename(filename)

            if (
                result["removed_chunks"] == 0
                and result["removed_source_documents"] == 0
                and int(result.get("removed_qdrant_points", 0)) == 0
            ):
                return Response(
                    {"error": "Không tìm thấy tài liệu tương ứng để xóa"},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {
                    "success": True,
                    "message": f"Đã xóa tài liệu: {filename}",
                    "filename": filename,
                    "removed_chunks": result["removed_chunks"],
                    "removed_source_documents": result["removed_source_documents"],
                    "removed_qdrant_points": result.get("removed_qdrant_points", 0),
                    "document_count": result["document_count"],
                    "uploaded_files": result["uploaded_files"],
                }
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {"error": f"Lỗi xóa tài liệu: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChunkStrategyEvaluationView(APIView):
    """
    API endpoint để đánh giá chunk strategy
    POST /api/chunk-strategy/evaluate/
    """

    parser_classes = [JSONParser]

    DEFAULT_CHUNK_SIZES = [500, 1000, 1500, 2000]
    DEFAULT_CHUNK_OVERLAPS = [50, 100, 200]

    def post(self, request):
        evaluation_set = request.data.get('evaluation_set', [])
        chunk_sizes = request.data.get('chunk_sizes', self.DEFAULT_CHUNK_SIZES)
        chunk_overlaps = request.data.get('chunk_overlaps', self.DEFAULT_CHUNK_OVERLAPS)
        top_k = request.data.get('top_k', 3)

        if not isinstance(evaluation_set, list) or not evaluation_set:
            return Response(
                {"error": "evaluation_set phải là danh sách và không được rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(chunk_sizes, list) or not chunk_sizes:
            return Response(
                {"error": "chunk_sizes phải là danh sách không rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(chunk_overlaps, list) or not chunk_overlaps:
            return Response(
                {"error": "chunk_overlaps phải là danh sách không rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_chunk_sizes = [_parse_int(item, 'chunk_size', min_value=1) for item in chunk_sizes]
            parsed_chunk_overlaps = [_parse_int(item, 'chunk_overlap', min_value=0) for item in chunk_overlaps]
            parsed_top_k = _parse_int(top_k, 'top_k', min_value=1)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        rag_engine = _get_rag_engine()
        try:
            report = rag_engine.evaluate_chunk_strategy(
                evaluation_set=evaluation_set,
                chunk_sizes=[item for item in parsed_chunk_sizes if item is not None],
                chunk_overlaps=[item for item in parsed_chunk_overlaps if item is not None],
                top_k=parsed_top_k or 3,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {"error": f"Lỗi đánh giá chunk strategy: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "chunk_sizes": [item for item in parsed_chunk_sizes if item is not None],
                "chunk_overlaps": [item for item in parsed_chunk_overlaps if item is not None],
                "top_k": parsed_top_k,
                **report,
            }
        )


class RetrievalBenchmarkView(APIView):
    """
    API endpoint benchmark retrieval modes
    POST /api/retrieval/benchmark/
    """

    parser_classes = [JSONParser]
    DEFAULT_RETRIEVAL_MODES = ["vector", "hybrid", "hybrid_rerank", "hybrid_multivector"]

    def post(self, request):
        evaluation_set = request.data.get('evaluation_set', [])
        top_k_raw = request.data.get('top_k', 3)
        retrieval_modes_raw = request.data.get('retrieval_modes', self.DEFAULT_RETRIEVAL_MODES)

        if not isinstance(evaluation_set, list) or not evaluation_set:
            return Response(
                {"error": "evaluation_set phải là danh sách và không được rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(retrieval_modes_raw, list) or not retrieval_modes_raw:
            return Response(
                {"error": "retrieval_modes phải là danh sách không rỗng"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_top_k = _parse_int(top_k_raw, 'top_k', min_value=1)
            retrieval_modes = [str(item).strip().lower() for item in retrieval_modes_raw if str(item).strip()]
            metadata_filters = _build_metadata_filters(request.data)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

        rag_engine = _get_rag_engine()
        try:
            report = rag_engine.benchmark_retrieval_modes(
                evaluation_set=evaluation_set,
                top_k=parsed_top_k or 3,
                retrieval_modes=retrieval_modes,
                metadata_filters=metadata_filters,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {"error": f"Lỗi benchmark retrieval: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "top_k": parsed_top_k,
                "retrieval_modes": retrieval_modes,
                "applied_filters": metadata_filters,
                **report,
            }
        )
