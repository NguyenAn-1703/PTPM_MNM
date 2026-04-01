"""CLI utility to ingest documents from data/raw into the current RAG index."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import sys


def _setup_django() -> None:
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")

    import django

    django.setup()


def main() -> None:
    _setup_django()

    from src.ingestion.loader import list_raw_documents
    from src.ingestion.processor import extract_document_text
    from src.rag.runtime import get_rag_engine

    rag_engine = get_rag_engine()
    files = list_raw_documents()

    if not files:
        print("Không tìm thấy file nào trong backend/data/raw")
        return

    total_chunks = 0
    for path in files:
        text = extract_document_text(path)
        if not text.strip():
            print(f"Bo qua file rong: {path.name}")
            continue

        chunks = rag_engine.add_documents(
            text=text,
            metadata={
                "filename": path.name,
                "file_type": path.suffix.lower().lstrip("."),
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        total_chunks += chunks
        print(f"Indexed {path.name}: {chunks} chunks")

    print(f"Done. Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    main()
