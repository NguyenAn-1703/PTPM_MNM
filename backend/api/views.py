"""
API Views for RAG System
"""
import os
import tempfile
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status


def _get_rag_engine():
    from .utils.rag_engine import get_rag_engine
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


class UploadDocumentView(APIView):
    """
    API endpoint để upload tài liệu
    POST /api/upload/
    """
    parser_classes = [MultiPartParser, FormParser]
    
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'bmp', 'tiff']
    IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff']
    
    def post(self, request):
        from .utils.document_processor import process_document, get_file_extension, extract_pdf_pages

        if 'file' not in request.FILES:
            return Response(
                {"error": "Không tìm thấy file trong request"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        filename = uploaded_file.name
        file_ext = get_file_extension(filename)
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
        
        # Validate file extension
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return Response(
                {"error": f"Định dạng file không hỗ trợ: {file_ext}. Chỉ hỗ trợ: {', '.join(self.ALLOWED_EXTENSIONS)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # Extract text from document
            text = process_document(tmp_path, file_ext)
            source_segments = None

            if file_ext == 'pdf':
                source_segments = extract_pdf_pages(tmp_path)
            
            if not text.strip():
                error_message = "Không thể trích xuất text từ tài liệu. File có thể rỗng hoặc không có nội dung chữ."
                if file_ext in self.IMAGE_EXTENSIONS:
                    error_message = (
                        "OCR không trích xuất được text từ ảnh. "
                        "Kiểm tra ảnh có chữ rõ ràng và đảm bảo Tesseract + gói ngôn ngữ đã được cài đặt đúng."
                    )
                return Response(
                    {"error": error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add to vector store
            rag_engine = _get_rag_engine()
            chunks_added = rag_engine.add_documents(
                text=text,
                metadata={
                    "filename": filename,
                    "file_type": file_ext
                },
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                source_segments=source_segments,
            )
            
            # Cleanup temp file
            os.unlink(tmp_path)
            
            return Response({
                "success": True,
                "message": f"Đã xử lý thành công file: {filename}",
                "filename": filename,
                "file_type": file_ext,
                "text_length": len(text),
                "chunks_added": chunks_added,
                "chunk_size": chunk_size or rag_engine.chunk_size,
                "chunk_overlap": chunk_overlap or rag_engine.chunk_overlap,
            })
            
        except Exception as e:
            # Cleanup temp file if exists
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
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
        
        if not question:
            return Response(
                {"error": "Câu hỏi không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            history = self._parse_history(history_raw)
            session_id = self._parse_session_id(session_id_raw)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rag_engine = _get_rag_engine()
            result = rag_engine.chat(question, history=history, session_id=session_id)
            
            return Response({
                "success": True,
                "question": question,
                "answer": result["answer"],
                "contexts": result["contexts"],
                "has_context": result["has_context"],
                "session_id": result.get("session_id"),
                "standalone_question": result.get("standalone_question", question),
                "rewritten": bool(result.get("rewritten", False)),
            })
            
        except Exception as e:
            return Response(
                {"error": f"Lỗi xử lý câu hỏi: {str(e)}"},
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
