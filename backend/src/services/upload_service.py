"""Application service for upload parsing and indexing workflows."""
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.ingestion.archive import persist_uploaded_artifacts
from src.ingestion.document_processor import extract_pdf_text_with_pages, get_file_extension, process_document
from src.llm.runtime import get_rag_engine


logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ["pdf", "docx", "doc", "png", "jpg", "jpeg", "bmp", "tiff"]
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "bmp", "tiff"]


def process_single_upload(uploaded_file, chunk_size: Optional[int], chunk_overlap: Optional[int], owner_session_id: Optional[str] = None) -> Dict[str, Any]:
    filename = uploaded_file.name
    file_ext = get_file_extension(filename)

    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Định dạng file không hỗ trợ: {file_ext}. Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
        for chunk in uploaded_file.chunks():
            tmp_file.write(chunk)
        tmp_path = tmp_file.name

    try:
        source_segments = None
        if file_ext == "pdf":
            pdf_data = extract_pdf_text_with_pages(tmp_path)
            text = str(pdf_data.get("text", ""))
            source_segments = pdf_data.get("pages") or []
        else:
            text = process_document(tmp_path, file_ext)

        if not text.strip():
            error_message = "Không thể trích xuất text từ tài liệu. File có thể rỗng hoặc không có nội dung chữ."
            if file_ext in IMAGE_EXTENSIONS:
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
            logger.warning("Không thể lưu artifact vào data folder cho %s: %s", filename, exc)

        rag_engine = get_rag_engine()
        uploaded_at = datetime.utcnow()
        metadata = {
            "filename": filename,
            "file_type": file_ext,
            "uploaded_at": uploaded_at.isoformat() + "Z",
            "uploaded_at_ts": uploaded_at.timestamp(),
        }
        if owner_session_id:
            metadata["owner_session_id"] = owner_session_id
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


def process_upload_batch(uploaded_files, chunk_size: Optional[int], chunk_overlap: Optional[int], owner_session_id: Optional[str] = None) -> Dict[str, Any]:
    processed_files: List[Dict[str, Any]] = []
    total_chunks_added = 0
    total_text_length = 0

    for uploaded_file in uploaded_files:
        file_result = process_single_upload(
            uploaded_file=uploaded_file,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            owner_session_id=owner_session_id,
        )
        processed_files.append(file_result)
        total_chunks_added += int(file_result["chunks_added"])
        total_text_length += int(file_result["text_length"])

    return {
        "processed_files": processed_files,
        "total_chunks_added": total_chunks_added,
        "total_text_length": total_text_length,
    }
