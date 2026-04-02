"""Document extraction and text chunk preparation helpers."""
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ingestion.document_processor import process_document
from src.llm.text import normalize_chunk_params, split_text_with_offsets


def extract_document_text(path: Path) -> str:
    file_ext = path.suffix.lower().lstrip(".")
    return process_document(str(path), file_ext)


def split_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    base_offset: int = 0,
    strategy: str = "fixed",
) -> List[Dict[str, Any]]:
    normalized_size, normalized_overlap = normalize_chunk_params(
        default_size=chunk_size,
        default_overlap=chunk_overlap,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return split_text_with_offsets(
        text,
        chunk_size=normalized_size,
        chunk_overlap=normalized_overlap,
        base_offset=base_offset,
        strategy=strategy,
    )


def build_metadata(filename: str, file_type: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"filename": filename, "file_type": file_type}
    if extra:
        payload.update(extra)
    return payload
