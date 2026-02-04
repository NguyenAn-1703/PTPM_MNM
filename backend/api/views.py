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

from .utils.document_processor import process_document, get_file_extension
from .utils.rag_engine import get_rag_engine


class UploadDocumentView(APIView):
    """
    API endpoint để upload tài liệu
    POST /api/upload/
    """
    parser_classes = [MultiPartParser, FormParser]
    
    ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'bmp', 'tiff']
    
    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {"error": "Không tìm thấy file trong request"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        filename = uploaded_file.name
        file_ext = get_file_extension(filename)
        
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
            
            if not text.strip():
                return Response(
                    {"error": "Không thể trích xuất text từ tài liệu. File có thể rỗng hoặc chỉ chứa hình ảnh."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add to vector store
            rag_engine = get_rag_engine()
            chunks_added = rag_engine.add_documents(
                text=text,
                metadata={
                    "filename": filename,
                    "file_type": file_ext
                }
            )
            
            # Cleanup temp file
            os.unlink(tmp_path)
            
            return Response({
                "success": True,
                "message": f"Đã xử lý thành công file: {filename}",
                "filename": filename,
                "file_type": file_ext,
                "text_length": len(text),
                "chunks_added": chunks_added
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
    
    def post(self, request):
        question = request.data.get('question', '').strip()
        
        if not question:
            return Response(
                {"error": "Câu hỏi không được để trống"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rag_engine = get_rag_engine()
            result = rag_engine.chat(question)
            
            return Response({
                "success": True,
                "question": question,
                "answer": result["answer"],
                "contexts": result["contexts"],
                "has_context": result["has_context"]
            })
            
        except Exception as e:
            return Response(
                {"error": f"Lỗi xử lý câu hỏi: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatusView(APIView):
    """
    API endpoint để kiểm tra trạng thái hệ thống
    GET /api/status/
    """
    def get(self, request):
        try:
            rag_engine = get_rag_engine()
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
            rag_engine = get_rag_engine()
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
