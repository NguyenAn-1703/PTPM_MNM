"""
API Views for RAG System
"""
import json
import logging
import re
import shutil
from typing import List
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework import status
import uuid

from src.controllers import ChatFlowController
from src.services import upload_service


logger = logging.getLogger(__name__)


ALLOWED_RETRIEVAL_MODES = {'vector', 'hybrid', 'hybrid_rerank', 'hybrid_multivector'}
LEGACY_OWNER_SESSION_ID = "legacy"


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


def _parse_retrieval_mode(value) -> str:
    mode = str(value or 'hybrid').strip().lower()
    if mode not in ALLOWED_RETRIEVAL_MODES:
        raise ValueError("retrieval_mode phải là vector, hybrid, hybrid_rerank hoặc hybrid_multivector")
    return mode


def _error_response(message: str, status_code: int, error_code: str, details=None):
    payload = {
        "success": False,
        "error": message,
        "error_code": error_code,
    }
    if details is not None:
        payload["error_details"] = details
    return Response(payload, status=status_code)


def _parse_session_id(session_id_raw, required: bool = False):
    if session_id_raw in (None, ""):
        if required:
            raise ValueError("session_id không được để trống")
        return None

    session_id = str(session_id_raw).strip()
    if not session_id:
        if required:
            raise ValueError("session_id không được để trống")
        return None

    if len(session_id) > 128:
        raise ValueError("session_id không được dài quá 128 ký tự")

    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        raise ValueError("session_id chỉ được chứa chữ, số, dấu gạch ngang và gạch dưới")

    return session_id


def _parse_non_empty_list(value, field_name: str) -> list:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} phải là danh sách và không được rỗng")
    return value


def _build_metadata_filters(request_data) -> dict:
    metadata_filters = {
        "filenames": _parse_string_list(request_data.get("filenames", [])),
        "file_types": _parse_string_list(request_data.get("file_types", [])),
        "owner_session_ids": _parse_string_list(request_data.get("owner_session_ids", [])),
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
    
    def post(self, request):
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files and 'file' in request.FILES:
            uploaded_files = [request.FILES['file']]

        if not uploaded_files:
            return _error_response("Không tìm thấy file trong request", status.HTTP_400_BAD_REQUEST, "UPLOAD_NO_FILE")

        chunk_size_raw = request.data.get('chunk_size')
        chunk_overlap_raw = request.data.get('chunk_overlap')
        upload_session_id_raw = request.data.get('session_id')

        try:
            chunk_size = _parse_int(chunk_size_raw, 'chunk_size', min_value=1)
            chunk_overlap = _parse_int(chunk_overlap_raw, 'chunk_overlap', min_value=0)
            upload_session_id = _parse_session_id(upload_session_id_raw)
            if chunk_size is not None and chunk_overlap is not None and chunk_overlap >= chunk_size:
                return _error_response("chunk_overlap phải nhỏ hơn chunk_size", status.HTTP_400_BAD_REQUEST, "UPLOAD_INVALID_CHUNK_PARAMS")
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "UPLOAD_INVALID_REQUEST")
        
        try:
            batch_result = upload_service.process_upload_batch(
                uploaded_files=uploaded_files,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                owner_session_id=upload_session_id,
            )
            processed_files = batch_result["processed_files"]
            total_chunks_added = int(batch_result["total_chunks_added"])
            total_text_length = int(batch_result["total_text_length"])

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
            return _error_response(f"Lỗi xử lý file: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR, "UPLOAD_PROCESSING_FAILED")


class ChatView(APIView):
    """
    API endpoint để chat với RAG
    POST /api/chat/
    """
    parser_classes = [JSONParser]

    @staticmethod
    def _parse_history(history_raw):
        return ChatFlowController.parse_history(history_raw)

    @staticmethod
    def _parse_session_id(session_id_raw):
        return _parse_session_id(session_id_raw)
    
    def post(self, request):
        question = request.data.get('question', '').strip()
        history_raw = request.data.get('history', [])
        session_id_raw = request.data.get('session_id')
        retrieval_mode_raw = request.data.get('retrieval_mode', 'hybrid')
        use_reranker_raw = request.data.get('use_reranker', True)
        use_self_rag_raw = request.data.get('use_self_rag', True)
        trace_id = _parse_trace_id(request)
        
        if not question:
            return _error_response("Câu hỏi không được để trống", status.HTTP_400_BAD_REQUEST, "CHAT_EMPTY_QUESTION")

        top_k_raw = request.data.get('top_k', ChatFlowController.default_top_k())

        try:
            history = self._parse_history(history_raw)
            session_id = self._parse_session_id(session_id_raw)
            use_reranker = _parse_bool(use_reranker_raw, 'use_reranker')
            use_self_rag = _parse_bool(use_self_rag_raw, 'use_self_rag')
            retrieval_mode = _parse_retrieval_mode(retrieval_mode_raw)
            top_k = _parse_int(top_k_raw, 'top_k', min_value=1) or ChatFlowController.default_top_k()

            metadata_filters = _build_metadata_filters(request.data)
            if session_id and not metadata_filters.get("owner_session_ids"):
                metadata_filters["owner_session_ids"] = [session_id, LEGACY_OWNER_SESSION_ID]
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "CHAT_INVALID_REQUEST")
        
        try:
            result = ChatFlowController.run_chat(
                question=question,
                history=history,
                top_k=top_k,
                session_id=session_id,
                retrieval_mode=retrieval_mode,
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
                "retrieval_mode": result.get("retrieval_mode", retrieval_mode),
                "top_k": result.get("top_k", top_k),
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
            return _error_response(f"Lỗi xử lý câu hỏi: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR, "CHAT_PROCESSING_FAILED")


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
            return _error_response("Câu hỏi không được để trống", status.HTTP_400_BAD_REQUEST, "CHAT_STREAM_EMPTY_QUESTION")

        try:
            history = ChatView._parse_history(request.data.get('history', []))
            session_id = _parse_session_id(request.data.get('session_id'))
            retrieval_mode = _parse_retrieval_mode(request.data.get('retrieval_mode', 'hybrid'))
            top_k_raw = request.data.get('top_k', ChatFlowController.default_top_k())
            top_k = _parse_int(top_k_raw, 'top_k', min_value=1) or ChatFlowController.default_top_k()

            use_reranker = _parse_bool(request.data.get('use_reranker', True), 'use_reranker')
            use_self_rag = _parse_bool(request.data.get('use_self_rag', True), 'use_self_rag')
            metadata_filters = _build_metadata_filters(request.data)
            if session_id and not metadata_filters.get("owner_session_ids"):
                metadata_filters["owner_session_ids"] = [session_id, LEGACY_OWNER_SESSION_ID]
            trace_id = _parse_trace_id(request)
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "CHAT_STREAM_INVALID_REQUEST")


        def _event_stream():
            try:
                for event in ChatFlowController.run_chat_stream(
                    question=question,
                    history=history,
                    top_k=top_k,
                    session_id=session_id,
                    retrieval_mode=retrieval_mode,
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
        retrieval_mode_raw = request.data.get('retrieval_mode', 'hybrid')
        run_ragas_raw = request.data.get('run_ragas', False)
        persist_artifact_raw = request.data.get('persist_artifact', False)

        try:
            _parse_non_empty_list(evaluation_set, 'evaluation_set')
            top_k = _parse_int(request.data.get('top_k', 3), 'top_k', min_value=1)
            run_ragas = _parse_bool(run_ragas_raw, 'run_ragas')
            persist_artifact = _parse_bool(persist_artifact_raw, 'persist_artifact')
            retrieval_mode = _parse_retrieval_mode(retrieval_mode_raw)
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "SELF_RAG_CALIBRATE_INVALID_REQUEST")

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
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "SELF_RAG_CALIBRATE_INVALID_INPUT")
        except Exception as exc:
            return _error_response(
                f"Lỗi calibrate self-rag: {str(exc)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SELF_RAG_CALIBRATE_FAILED",
            )


class ClearSessionMemoryView(APIView):
    """
    API endpoint để xóa memory hội thoại theo session_id
    POST /api/chat/memory/clear/
    """

    parser_classes = [JSONParser]

    def post(self, request):
        try:
            session_id = _parse_session_id(request.data.get('session_id'), required=True)
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "SESSION_INVALID_ID")

        try:
            cleared = ChatFlowController.clear_session_memory(session_id)
            return Response(
                {
                    "success": True,
                    "session_id": session_id,
                    "cleared": cleared,
                    "message": "Đã reset ngữ cảnh hội thoại cho session" if cleared else "Session chưa có memory để xóa",
                }
            )
        except Exception as e:
            return _error_response(f"Lỗi xóa memory hội thoại: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR, "SESSION_CLEAR_FAILED")


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
            return _error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR, "STATUS_FETCH_FAILED")


class ClearVectorStoreView(APIView):
    """
    API endpoint để xóa vector store
    DELETE /api/clear/
    """
    parser_classes = [JSONParser]

    @staticmethod
    def _clear_local_data_directories():
        from src.config import get_rag_settings

        cfg = get_rag_settings()
        target_dirs = [cfg.data_raw_dir, cfg.data_processed_dir]
        cleared_dirs = []

        for target_dir in target_dirs:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            cleared_dirs.append(str(target_dir))

        return cleared_dirs

    def delete(self, request):
        try:
            clear_local_data_raw = request.data.get('clear_local_data', request.query_params.get('clear_local_data'))
            clear_local_data = False
            if clear_local_data_raw not in (None, ''):
                clear_local_data = _parse_bool(clear_local_data_raw, 'clear_local_data')

            rag_engine = _get_rag_engine()
            rag_engine.clear_vector_store()

            response_payload = {
                "success": True,
                "message": "Đã xóa toàn bộ dữ liệu vector store",
                "cleared_local_data": False,
            }

            if clear_local_data:
                cleared_dirs = self._clear_local_data_directories()
                response_payload["message"] = "Đã xóa vector store và dữ liệu local"
                response_payload["cleared_local_data"] = True
                response_payload["cleared_local_directories"] = cleared_dirs
            
            return Response(response_payload)
        except ValueError as e:
            return _error_response(str(e), status.HTTP_400_BAD_REQUEST, "VECTOR_CLEAR_INVALID_REQUEST")
        except Exception as e:
            return _error_response(
                f"Lỗi xóa vector store: {str(e)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "VECTOR_CLEAR_FAILED",
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
            return _error_response("filename không được để trống", status.HTTP_400_BAD_REQUEST, "DOCUMENT_DELETE_EMPTY_FILENAME")

        if len(filename) > 255:
            return _error_response(
                "filename không được dài quá 255 ký tự",
                status.HTTP_400_BAD_REQUEST,
                "DOCUMENT_DELETE_INVALID_FILENAME",
            )

        try:
            rag_engine = _get_rag_engine()
            result = rag_engine.delete_documents_by_filename(filename)

            if (
                result["removed_chunks"] == 0
                and result["removed_source_documents"] == 0
                and int(result.get("removed_qdrant_points", 0)) == 0
            ):
                return _error_response(
                    "Không tìm thấy tài liệu tương ứng để xóa",
                    status.HTTP_404_NOT_FOUND,
                    "DOCUMENT_NOT_FOUND",
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
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "DOCUMENT_DELETE_INVALID_REQUEST")
        except Exception as exc:
            return _error_response(
                f"Lỗi xóa tài liệu: {str(exc)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "DOCUMENT_DELETE_FAILED",
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

        try:
            _parse_non_empty_list(evaluation_set, 'evaluation_set')
            _parse_non_empty_list(chunk_sizes, 'chunk_sizes')
            _parse_non_empty_list(chunk_overlaps, 'chunk_overlaps')
            parsed_chunk_sizes = [_parse_int(item, 'chunk_size', min_value=1) for item in chunk_sizes]
            parsed_chunk_overlaps = [_parse_int(item, 'chunk_overlap', min_value=0) for item in chunk_overlaps]
            parsed_top_k = _parse_int(top_k, 'top_k', min_value=1)
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "CHUNK_STRATEGY_INVALID_REQUEST")

        rag_engine = _get_rag_engine()
        try:
            report = rag_engine.evaluate_chunk_strategy(
                evaluation_set=evaluation_set,
                chunk_sizes=[item for item in parsed_chunk_sizes if item is not None],
                chunk_overlaps=[item for item in parsed_chunk_overlaps if item is not None],
                top_k=parsed_top_k or 3,
            )
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "CHUNK_STRATEGY_INVALID_INPUT")
        except Exception as exc:
            return _error_response(
                f"Lỗi đánh giá chunk strategy: {str(exc)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "CHUNK_STRATEGY_EVALUATION_FAILED",
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

        try:
            _parse_non_empty_list(evaluation_set, 'evaluation_set')
            _parse_non_empty_list(retrieval_modes_raw, 'retrieval_modes')
            parsed_top_k = _parse_int(top_k_raw, 'top_k', min_value=1)
            retrieval_modes = [str(item).strip().lower() for item in retrieval_modes_raw if str(item).strip()]
            if not retrieval_modes:
                raise ValueError("retrieval_modes phải có ít nhất một giá trị hợp lệ")
            metadata_filters = _build_metadata_filters(request.data)
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "RETRIEVAL_BENCHMARK_INVALID_REQUEST")

        rag_engine = _get_rag_engine()
        try:
            report = rag_engine.benchmark_retrieval_modes(
                evaluation_set=evaluation_set,
                top_k=parsed_top_k or 3,
                retrieval_modes=retrieval_modes,
                metadata_filters=metadata_filters,
            )
        except ValueError as exc:
            return _error_response(str(exc), status.HTTP_400_BAD_REQUEST, "RETRIEVAL_BENCHMARK_INVALID_INPUT")
        except Exception as exc:
            return _error_response(
                f"Lỗi benchmark retrieval: {str(exc)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "RETRIEVAL_BENCHMARK_FAILED",
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
