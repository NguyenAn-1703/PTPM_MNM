"""Inspect owner_session_id distribution in source registry and FAISS docstore.

Usage:
    cd backend
    .venv/bin/python test/test_owner_session_distribution.py
    .venv/bin/python test/test_owner_session_distribution.py --top 10 --as-json
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
import sys
from typing import Dict, Tuple


def _setup_django() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()


def _count_source_owners(storage) -> Counter:
    counter: Counter = Counter()
    for item in storage.load_source_documents():
        metadata = item.get("metadata") if isinstance(item, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        owner = str(metadata.get("owner_session_id", "")).strip() or "<missing>"
        counter[owner] += 1
    return counter


def _count_vector_owners(storage, embeddings) -> Tuple[Counter, bool]:
    vector_store = storage.load_vector_store(embeddings)
    if vector_store is None:
        return Counter(), False

    counter: Counter = Counter()
    for doc in vector_store.docstore._dict.values():
        metadata = doc.metadata or {}
        owner = str(metadata.get("owner_session_id", "")).strip() or "<missing>"
        counter[owner] += 1

    return counter, True


def _counter_to_top_dict(counter: Counter, top_n: int) -> Dict[str, int]:
    return {key: int(value) for key, value in counter.most_common(max(1, top_n))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect owner_session_id distribution")
    parser.add_argument("--top", type=int, default=20, help="Top N owners to print")
    parser.add_argument("--as-json", action="store_true", help="Print output as JSON")

    args = parser.parse_args()

    _setup_django()

    from src.database import get_storage
    from src.model_factory import get_embeddings

    storage = get_storage()
    embeddings = get_embeddings()

    source_counter = _count_source_owners(storage)
    vector_counter, has_vector_store = _count_vector_owners(storage, embeddings)

    payload = {
        "source_documents": {
            "total": int(sum(source_counter.values())),
            "unique_owners": int(len(source_counter)),
            "top_owners": _counter_to_top_dict(source_counter, args.top),
        },
        "faiss_docstore": {
            "available": bool(has_vector_store),
            "total": int(sum(vector_counter.values())) if has_vector_store else 0,
            "unique_owners": int(len(vector_counter)) if has_vector_store else 0,
            "top_owners": _counter_to_top_dict(vector_counter, args.top) if has_vector_store else {},
        },
    }

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print("=== Owner Session Distribution ===")
    print("\n[source_documents]")
    print(f"- total: {payload['source_documents']['total']}")
    print(f"- unique_owners: {payload['source_documents']['unique_owners']}")
    for owner, count in payload["source_documents"]["top_owners"].items():
        print(f"  - {owner}: {count}")

    print("\n[faiss_docstore]")
    print(f"- available: {payload['faiss_docstore']['available']}")
    if payload["faiss_docstore"]["available"]:
        print(f"- total: {payload['faiss_docstore']['total']}")
        print(f"- unique_owners: {payload['faiss_docstore']['unique_owners']}")
        for owner, count in payload["faiss_docstore"]["top_owners"].items():
            print(f"  - {owner}: {count}")


if __name__ == "__main__":
    main()
