"""Benchmark SSE streaming latency for /api/chat/stream/.

Usage:
    cd backend
    .venv/bin/python test/benchmark_stream_latency.py
    .venv/bin/python test/benchmark_stream_latency.py --iterations 3 --max-questions 10
    .venv/bin/python test/benchmark_stream_latency.py --base-url http://127.0.0.1:8000/api --output stream_latency_report.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any, Dict, List

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"
DEFAULT_RETRIEVAL_MODE = "hybrid"
VALID_RETRIEVAL_MODES = {"vector", "hybrid", "hybrid_rerank", "hybrid_multivector"}


def _load_questions(path: Path, max_questions: int) -> List[str]:
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    if not isinstance(data, list) or not data:
        raise ValueError("evaluation file phai la JSON array va khong rong")

    questions: List[str] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"evaluation_set[{idx}] phai la object")
        question = str(item.get("question", "")).strip()
        if not question:
            raise ValueError(f"evaluation_set[{idx}].question khong hop le")
        questions.append(question)

    return questions[: max(1, max_questions)]


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


def _parse_sse_event(event_name: str, data_lines: List[str]) -> Dict[str, Any]:
    if not data_lines:
        return {"event": event_name, "data": {}}

    payload_text = "\n".join(data_lines)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        payload = {}

    return {"event": event_name, "data": payload}


def _stream_once(
    *,
    base_url: str,
    question: str,
    session_id: str,
    retrieval_mode: str,
    top_k: int,
    timeout: float,
) -> Dict[str, Any]:
    request_payload = {
        "question": question,
        "history": [],
        "session_id": session_id,
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "owner_session_ids": [session_id, "legacy"],
        "use_reranker": True,
        "use_self_rag": True,
    }

    started = time.perf_counter()
    with requests.post(
        f"{base_url}/chat/stream/",
        json=request_payload,
        headers={"Accept": "text/event-stream"},
        timeout=timeout,
        stream=True,
    ) as response:
        if response.status_code != 200:
            text = response.text[:500]
            raise RuntimeError(f"stream request failed with {response.status_code}: {text}")

        first_byte_ms: float | None = None
        first_token_ms: float | None = None
        token_events = 0
        token_chars = 0
        done_received = False

        current_event = "message"
        current_data_lines: List[str] = []

        def _flush_event() -> None:
            nonlocal first_token_ms, token_events, token_chars, done_received
            parsed = _parse_sse_event(current_event, current_data_lines)
            event_name = parsed["event"]
            data = parsed["data"]

            if event_name == "token":
                token = str(data.get("token", ""))
                if token:
                    token_events += 1
                    token_chars += len(token)
                    if first_token_ms is None:
                        first_token_ms = (time.perf_counter() - started) * 1000
                return

            if event_name == "error":
                raise RuntimeError(str(data.get("error", "stream returned error event")))

            if event_name == "done":
                done_received = True

        for raw_line in response.iter_lines(decode_unicode=True):
            if first_byte_ms is None:
                first_byte_ms = (time.perf_counter() - started) * 1000

            line = raw_line if raw_line is not None else ""
            if line == "":
                _flush_event()
                current_event = "message"
                current_data_lines = []
                continue

            if line.startswith("event:"):
                current_event = line[6:].strip() or "message"
                continue

            if line.startswith("data:"):
                current_data_lines.append(line[5:].strip())

        if current_data_lines:
            _flush_event()

        total_ms = (time.perf_counter() - started) * 1000

        if not done_received:
            raise RuntimeError("khong nhan duoc event done tu stream")

        return {
            "ttfb_ms": round(float(first_byte_ms or total_ms), 3),
            "first_token_ms": round(float(first_token_ms or total_ms), 3),
            "total_ms": round(total_ms, 3),
            "token_events": int(token_events),
            "token_chars": int(token_chars),
        }


def _summarize(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not samples:
        return {
            "samples": 0,
            "ttfb_ms": {},
            "first_token_ms": {},
            "total_ms": {},
            "token_events": {"avg": 0.0},
            "token_chars": {"avg": 0.0},
        }

    ttfb = [float(item["ttfb_ms"]) for item in samples]
    first_token = [float(item["first_token_ms"]) for item in samples]
    total = [float(item["total_ms"]) for item in samples]
    token_events = [int(item["token_events"]) for item in samples]
    token_chars = [int(item["token_chars"]) for item in samples]

    def _stat(values: List[float]) -> Dict[str, float]:
        return {
            "mean": round(statistics.fmean(values), 3),
            "p50": round(_percentile(values, 0.50), 3),
            "p95": round(_percentile(values, 0.95), 3),
            "max": round(max(values), 3),
        }

    return {
        "samples": len(samples),
        "ttfb_ms": _stat(ttfb),
        "first_token_ms": _stat(first_token),
        "total_ms": _stat(total),
        "token_events": {"avg": round(statistics.fmean(token_events), 3)},
        "token_chars": {"avg": round(statistics.fmean(token_chars), 3)},
    }


def _print_report(report: Dict[str, Any]) -> None:
    summary = report.get("summary", {})
    stats = report.get("stats", {})

    print("\n=== Stream Latency Benchmark ===")
    print(f"samples: {stats.get('samples', 0)}")
    print(f"questions: {summary.get('question_count', 0)}")
    print(f"iterations: {summary.get('iterations', 0)}")
    print(f"retrieval_mode: {summary.get('retrieval_mode')}")

    print("\nmetric         | mean    | p50     | p95     | max")
    print("-" * 56)

    for metric in ["ttfb_ms", "first_token_ms", "total_ms"]:
        metric_stats = stats.get(metric, {})
        print(
            f"{metric:<14} | "
            f"{metric_stats.get('mean', 0):>7.2f} | "
            f"{metric_stats.get('p50', 0):>7.2f} | "
            f"{metric_stats.get('p95', 0):>7.2f} | "
            f"{metric_stats.get('max', 0):>7.2f}"
        )

    token_events_avg = stats.get("token_events", {}).get("avg", 0)
    token_chars_avg = stats.get("token_chars", {}).get("avg", 0)
    print(f"\navg token_events: {token_events_avg}")
    print(f"avg token_chars: {token_chars_avg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark /api/chat/stream/ SSE latency")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--evaluation-file", default="evaluation_set.json", help="Evaluation set JSON")
    parser.add_argument("--iterations", type=int, default=2, help="Measured iterations")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup iterations")
    parser.add_argument("--max-questions", type=int, default=5, help="Max questions to run")
    parser.add_argument("--top-k", type=int, default=3, help="top_k for stream call")
    parser.add_argument(
        "--retrieval-mode",
        default=DEFAULT_RETRIEVAL_MODE,
        choices=sorted(VALID_RETRIEVAL_MODES),
        help="Retrieval mode",
    )
    parser.add_argument("--session-prefix", default="stream_bench", help="session_id prefix")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    parser.add_argument("--output", default="", help="Optional output JSON file")

    args = parser.parse_args()

    evaluation_path = Path(args.evaluation_file).expanduser().resolve()
    if not evaluation_path.exists():
        raise FileNotFoundError(f"Khong tim thay evaluation file: {evaluation_path}")

    questions = _load_questions(evaluation_path, max_questions=max(1, args.max_questions))

    iterations = max(1, int(args.iterations))
    warmup = max(0, int(args.warmup))
    top_k = max(1, int(args.top_k))
    timeout = max(5.0, float(args.timeout))

    # Warmup to stabilize first-call penalties.
    for warmup_idx in range(warmup):
        for q_idx, question in enumerate(questions):
            _stream_once(
                base_url=args.base_url.rstrip("/"),
                question=question,
                session_id=f"{args.session_prefix}_warmup_{warmup_idx}_{q_idx}",
                retrieval_mode=args.retrieval_mode,
                top_k=top_k,
                timeout=timeout,
            )

    samples: List[Dict[str, Any]] = []
    for iter_idx in range(iterations):
        for q_idx, question in enumerate(questions):
            sample = _stream_once(
                base_url=args.base_url.rstrip("/"),
                question=question,
                session_id=f"{args.session_prefix}_{iter_idx}_{q_idx}",
                retrieval_mode=args.retrieval_mode,
                top_k=top_k,
                timeout=timeout,
            )
            samples.append(sample)

    report = {
        "summary": {
            "base_url": args.base_url.rstrip("/"),
            "retrieval_mode": args.retrieval_mode,
            "question_count": len(questions),
            "iterations": iterations,
            "warmup": warmup,
            "top_k": top_k,
        },
        "stats": _summarize(samples),
        "samples": samples,
    }

    _print_report(report)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        with output_path.open("w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
        print(f"\nSaved report to: {output_path}")


if __name__ == "__main__":
    main()
