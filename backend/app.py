"""Small runtime entry helper for local backend diagnostics."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def _setup_django() -> None:
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")

    import django

    django.setup()


def run_status_snapshot() -> None:
    _setup_django()
    from src.rag.runtime import get_rag_engine

    stats = get_rag_engine().get_stats()
    print("RAG backend status snapshot")
    for key, value in stats.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    run_status_snapshot()
