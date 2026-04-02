"""Document loader utilities for data/raw directory."""
from pathlib import Path
from typing import Iterable, List

from ..config import get_rag_settings


SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}


def list_raw_documents(root: Path | None = None) -> List[Path]:
    cfg = get_rag_settings()
    base = root or cfg.data_raw_dir
    if not base.exists():
        return []

    files: List[Path] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def iter_raw_documents(root: Path | None = None) -> Iterable[Path]:
    for path in list_raw_documents(root):
        yield path
