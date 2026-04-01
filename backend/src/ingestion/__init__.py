"""Ingestion package: file loading, OCR, and text extraction."""

from .document_processor import extract_pdf_pages, get_file_extension, process_document
from .loader import iter_raw_documents, list_raw_documents
from .processor import build_metadata, extract_document_text, split_text

__all__ = [
    "extract_pdf_pages",
    "get_file_extension",
    "process_document",
    "iter_raw_documents",
    "list_raw_documents",
    "build_metadata",
    "extract_document_text",
    "split_text",
]
