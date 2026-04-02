"""Persist uploaded source files and extracted text artifacts under backend/data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Dict

from src.config import get_rag_settings


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document").name.strip() or "document"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def persist_uploaded_artifacts(tmp_path: str, original_filename: str, extracted_text: str) -> Dict[str, str]:
    cfg = get_rag_settings()
    raw_dir = cfg.data_raw_dir
    processed_dir = cfg.data_processed_dir

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    safe_name = _safe_filename(original_filename)
    raw_name = f"{timestamp}_{safe_name}"
    raw_path = raw_dir / raw_name
    shutil.copy2(tmp_path, raw_path)

    processed_name = f"{Path(raw_name).stem}.txt"
    processed_path = processed_dir / processed_name
    processed_path.write_text((extracted_text or "").strip(), encoding="utf-8")

    return {
        "raw_file": raw_name,
        "processed_file": processed_name,
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
    }
