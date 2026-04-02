"""Offline self-rag calibration pipeline with optional RAGAS metrics.

Usage:
    cd backend
    .venv/bin/python test_ragas_pipeline.py --evaluation-file evaluation_set.json --run-ragas
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


def _setup_django() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()


def _load_evaluation_set(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, list) or not data:
        raise ValueError("evaluation file phải là JSON array và không rỗng")

    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"evaluation_set[{idx}] phải là object")
        if not str(row.get("question", "")).strip():
            raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run self-rag calibration with optional RAGAS")
    parser.add_argument("--evaluation-file", default="evaluation_set.json", help="Path to evaluation set JSON")
    parser.add_argument("--top-k", type=int, default=3, help="Top-k contexts used during calibration")
    parser.add_argument("--retrieval-mode", default="hybrid", choices=["vector", "hybrid", "hybrid_multivector"])
    parser.add_argument("--run-ragas", action="store_true", help="Enable RAGAS metrics (requires ragas + datasets)")
    parser.add_argument("--persist-artifact", action="store_true", help="Persist calibration artifact JSON")

    args = parser.parse_args()

    _setup_django()

    evaluation_path = Path(args.evaluation_file).expanduser().resolve()
    if not evaluation_path.exists():
        raise FileNotFoundError(f"Không tìm thấy evaluation file: {evaluation_path}")

    evaluation_set = _load_evaluation_set(evaluation_path)

    from src.llm.runtime import get_rag_engine

    engine = get_rag_engine()
    report = engine.calibrate_self_rag_threshold(
        evaluation_set=evaluation_set,
        top_k=max(1, args.top_k),
        retrieval_mode="hybrid" if args.retrieval_mode == "hybrid_multivector" else args.retrieval_mode,
        run_ragas=bool(args.run_ragas),
        persist_artifact=bool(args.persist_artifact),
    )

    print("\n=== Self-RAG Calibration Report ===")
    print(f"threshold: {report.get('threshold')}")
    print(f"samples: {report.get('samples')}")
    print(f"metrics: {json.dumps(report.get('metrics', {}), ensure_ascii=False)}")

    ragas_report = report.get("ragas")
    if ragas_report is not None:
        print(f"ragas: {json.dumps(ragas_report, ensure_ascii=False)}")

    artifact_path = report.get("artifact_path")
    if artifact_path:
        print(f"artifact_path: {artifact_path}")


if __name__ == "__main__":
    main()
