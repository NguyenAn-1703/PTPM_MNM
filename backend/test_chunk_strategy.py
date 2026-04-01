"""
Benchmark chunk strategy for RAG retrieval accuracy.

Usage:
    cd backend
    python test_chunk_strategy.py
    python test_chunk_strategy.py --evaluation-file evaluation_set.json

Example evaluation_set.json:
[
  {
    "question": "Tài liệu nói gì về mục tiêu dự án?",
    "expected_keywords": ["mục tiêu", "dự án"]
  },
  {
    "question": "Mô hình LLM đang được dùng là gì?",
    "expected_keywords": ["qwen", "ollama"]
  }
]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


CHUNK_SIZES = [500, 1000, 1500, 2000]
CHUNK_OVERLAPS = [50, 100, 200]
DEFAULT_EVALUATION_FILE = "evaluation_set.json"


def _setup_django() -> None:
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")

    import django

    django.setup()


def _load_evaluation_set(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, list) or not data:
        raise ValueError("evaluation file phải là JSON array và không rỗng")

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"evaluation_set[{idx}] phải là object")
        if not str(item.get("question", "")).strip():
            raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")
        if "expected_keywords" in item and not isinstance(item["expected_keywords"], list):
            raise ValueError(f"evaluation_set[{idx}].expected_keywords phải là list")

    return data


def _print_summary(report: Dict[str, Any]) -> None:
    reports = report.get("reports", [])
    if not reports:
        print("Khong co ket qua de hien thi.")
        return

    print("\n=== Chunk Strategy Evaluation (retrieval_accuracy) ===")
    print("chunk_size | chunk_overlap | retrieval_accuracy | hits/total | generated_chunks")
    print("-" * 79)

    for item in reports:
        line = (
            f"{item['chunk_size']:>10} | "
            f"{item['chunk_overlap']:>13} | "
            f"{item['retrieval_accuracy']:>18.4f} | "
            f"{item['hits']}/{item['total_questions']:<10} | "
            f"{item['generated_chunks']}"
        )
        print(line)

    best = report.get("best_config")
    if best:
        print("\nBest config:")
        print(
            f"- chunk_size={best['chunk_size']}, "
            f"chunk_overlap={best['chunk_overlap']}, "
            f"retrieval_accuracy={best['retrieval_accuracy']:.4f}"
        )


def _resolve_evaluation_path(evaluation_file: str | None) -> Path:
    if evaluation_file:
        return Path(evaluation_file).expanduser().resolve()
    return (Path(__file__).resolve().parent / DEFAULT_EVALUATION_FILE).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG chunk strategy")
    parser.add_argument(
        "--evaluation-file",
        default=None,
        help=(
            "Path to JSON file containing evaluation_set "
            f"(default: {DEFAULT_EVALUATION_FILE} in current script directory)"
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of retrieved chunks per question",
    )
    parser.add_argument(
        "--output",
        default="chunk_strategy_report.json",
        help="Output report file (JSON)",
    )

    args = parser.parse_args()

    evaluation_path = _resolve_evaluation_path(args.evaluation_file)
    if not evaluation_path.exists():
        raise FileNotFoundError(
            "Khong tim thay evaluation file. "
            f"Hay tao file {evaluation_path} hoac truyen --evaluation-file <path>."
        )

    _setup_django()

    from src.rag.runtime import get_rag_engine

    evaluation_set = _load_evaluation_set(evaluation_path)
    rag_engine = get_rag_engine()

    report = rag_engine.evaluate_chunk_strategy(
        evaluation_set=evaluation_set,
        chunk_sizes=CHUNK_SIZES,
        chunk_overlaps=CHUNK_OVERLAPS,
        top_k=max(1, args.top_k),
    )

    output_path = Path(args.output).expanduser().resolve()
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)

    _print_summary(report)
    print(f"\nSaved report to: {output_path}")


if __name__ == "__main__":
    main()
