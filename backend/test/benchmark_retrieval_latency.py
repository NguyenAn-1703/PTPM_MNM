"""
Benchmark retrieval latency by mode (vector/hybrid/rerank/multivector).

Usage:
    cd backend
    .venv/bin/python test/benchmark_retrieval_latency.py
    .venv/bin/python test/benchmark_retrieval_latency.py --iterations 5 --warmup 1
    .venv/bin/python test/benchmark_retrieval_latency.py --modes hybrid,hybrid_rerank --output retrieval_latency_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List


DEFAULT_MODES = ["vector", "hybrid", "hybrid_rerank", "hybrid_multivector"]
VALID_MODES = set(DEFAULT_MODES)


def _setup_django() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()


def _load_questions(path: Path, max_questions: int) -> List[str]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, list) or not data:
        raise ValueError("evaluation file phải là JSON array và không rỗng")

    questions: List[str] = []
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"evaluation_set[{idx}] phải là object")
        question = str(row.get("question", "")).strip()
        if not question:
            raise ValueError(f"evaluation_set[{idx}].question không hợp lệ")
        questions.append(question)

    if max_questions > 0:
        questions = questions[:max_questions]

    return questions


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])

    ordered = sorted(values)
    position = (len(ordered) - 1) * pct
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])

    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _run_retrieval(engine: Any, mode: str, question: str, top_k: int) -> Dict[str, Any]:
    if mode == "vector":
        contexts = engine.search(question, top_k=max(top_k * 2, 6), metadata_filters=None)
        contexts = engine._filter_relevant_contexts(contexts)
        contexts = contexts[:top_k]
        return {"contexts": contexts, "reranker_used": False}

    if mode == "hybrid":
        contexts = engine._hybrid_search(question, top_k=max(top_k * 2, 6), metadata_filters=None)
        return {"contexts": contexts[:top_k], "reranker_used": False}

    if mode == "hybrid_multivector":
        original_multi_vector = bool(getattr(engine, "enable_multi_vector", False))
        engine.enable_multi_vector = True
        try:
            contexts = engine._hybrid_search(question, top_k=max(top_k * 2, 6), metadata_filters=None)
        finally:
            engine.enable_multi_vector = original_multi_vector
        return {"contexts": contexts[:top_k], "reranker_used": False}

    candidates = engine._hybrid_search(question, top_k=max(top_k * 2, 6), metadata_filters=None)
    rerank_info = engine._rerank_contexts(question, candidates, top_k=top_k)
    return {
        "contexts": rerank_info.get("contexts", []),
        "reranker_used": bool(rerank_info.get("used", False)),
    }


def _benchmark_mode(engine: Any, mode: str, questions: List[str], iterations: int, warmup: int, top_k: int) -> Dict[str, Any]:
    # Warmup keeps cache and Python hotspots out of measured loop.
    if warmup > 0 and questions:
        warmup_questions = questions[: min(len(questions), 5)]
        for _ in range(warmup):
            for question in warmup_questions:
                _run_retrieval(engine, mode, question, top_k)

    latencies_ms: List[float] = []
    context_counts: List[int] = []
    reranker_used_count = 0

    for _ in range(iterations):
        for question in questions:
            started = time.perf_counter()
            payload = _run_retrieval(engine, mode, question, top_k)
            elapsed_ms = (time.perf_counter() - started) * 1000

            contexts = payload.get("contexts", [])
            latencies_ms.append(elapsed_ms)
            context_counts.append(len(contexts))
            if payload.get("reranker_used"):
                reranker_used_count += 1

    if not latencies_ms:
        return {
            "mode": mode,
            "samples": 0,
            "avg_contexts": 0.0,
            "reranker_used_count": reranker_used_count,
            "mean_ms": 0.0,
            "std_ms": 0.0,
            "min_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
            "cache_stats": engine._retrieval_cache_stats(),
        }

    return {
        "mode": mode,
        "samples": len(latencies_ms),
        "avg_contexts": round(sum(context_counts) / len(context_counts), 3),
        "reranker_used_count": reranker_used_count,
        "mean_ms": round(statistics.fmean(latencies_ms), 3),
        "std_ms": round(statistics.pstdev(latencies_ms), 3) if len(latencies_ms) > 1 else 0.0,
        "min_ms": round(min(latencies_ms), 3),
        "p50_ms": round(_percentile(latencies_ms, 0.50), 3),
        "p95_ms": round(_percentile(latencies_ms, 0.95), 3),
        "p99_ms": round(_percentile(latencies_ms, 0.99), 3),
        "max_ms": round(max(latencies_ms), 3),
        "cache_stats": engine._retrieval_cache_stats(),
    }


def _parse_modes(raw_modes: str) -> List[str]:
    modes = [item.strip().lower() for item in raw_modes.split(",") if item.strip()]
    if not modes:
        raise ValueError("modes không được để trống")

    deduped: List[str] = []
    for mode in modes:
        if mode not in VALID_MODES:
            raise ValueError(f"mode không hợp lệ: {mode}")
        if mode not in deduped:
            deduped.append(mode)

    return deduped


def _print_report(report: Dict[str, Any]) -> None:
    print("\n=== Retrieval Latency Benchmark (ms) ===")
    print("mode | samples | mean | p50 | p95 | p99 | min | max | avg_ctx")
    print("-" * 88)

    for row in report.get("reports", []):
        print(
            f"{row['mode']:<18} | "
            f"{row['samples']:>7} | "
            f"{row['mean_ms']:>5.1f} | "
            f"{row['p50_ms']:>5.1f} | "
            f"{row['p95_ms']:>5.1f} | "
            f"{row['p99_ms']:>5.1f} | "
            f"{row['min_ms']:>5.1f} | "
            f"{row['max_ms']:>5.1f} | "
            f"{row['avg_contexts']:>7.2f}"
        )

    print("\nCache stats snapshot:")
    print(json.dumps(report.get("cache_stats", {}), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark retrieval latency by mode")
    parser.add_argument("--evaluation-file", default="evaluation_set.json", help="Path to evaluation_set JSON")
    parser.add_argument("--iterations", type=int, default=3, help="Measured iterations over all questions")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup iterations before measuring")
    parser.add_argument("--top-k", type=int, default=3, help="Top-K contexts")
    parser.add_argument("--max-questions", type=int, default=20, help="Max number of questions to benchmark")
    parser.add_argument("--modes", default=",".join(DEFAULT_MODES), help="Comma-separated retrieval modes")
    parser.add_argument("--output", default="", help="Optional output JSON path")

    args = parser.parse_args()

    evaluation_path = Path(args.evaluation_file).expanduser().resolve()
    if not evaluation_path.exists():
        raise FileNotFoundError(f"Không tìm thấy evaluation file: {evaluation_path}")

    iterations = max(1, int(args.iterations))
    warmup = max(0, int(args.warmup))
    top_k = max(1, int(args.top_k))
    max_questions = max(1, int(args.max_questions))
    modes = _parse_modes(args.modes)

    _setup_django()

    from src.llm.runtime import get_rag_engine

    engine = get_rag_engine()
    if engine.vector_store is None and not bool(getattr(engine, "vector_adapter", None) and engine.vector_adapter.should_use_as_primary()):
        payload = {
            "summary": {
                "questions": 0,
                "iterations": iterations,
                "warmup": warmup,
                "top_k": top_k,
                "modes": modes,
                "skipped": True,
                "reason": "empty_vector_store",
            },
            "reports": [],
            "cache_stats": engine._retrieval_cache_stats(),
        }
        print("Khong co du lieu vector store. Bo qua benchmark.")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    questions = _load_questions(evaluation_path, max_questions=max_questions)

    reports: List[Dict[str, Any]] = []
    for mode in modes:
        reports.append(_benchmark_mode(engine, mode=mode, questions=questions, iterations=iterations, warmup=warmup, top_k=top_k))

    reports.sort(key=lambda item: item.get("p95_ms", 0.0))
    payload = {
        "summary": {
            "questions": len(questions),
            "iterations": iterations,
            "warmup": warmup,
            "top_k": top_k,
            "modes": modes,
        },
        "reports": reports,
        "cache_stats": engine._retrieval_cache_stats(),
    }

    _print_report(payload)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        with output_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
        print(f"\nSaved report to: {output_path}")


if __name__ == "__main__":
    main()
