"""Run multiple backend utility scripts from one command.

Usage:
    cd backend
    .venv/bin/python test/run_test_suite.py --suite quick
    .venv/bin/python test/run_test_suite.py --suite full --include-heavy --strict
    .venv/bin/python test/run_test_suite.py --only ocr,owner_distribution,owner_remap
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Sequence

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"


@dataclass(frozen=True)
class ScriptSpec:
    script_id: str
    path: str
    description: str
    requires_server: bool = False
    heavy: bool = False


SCRIPT_SPECS: Dict[str, ScriptSpec] = {
    "ocr": ScriptSpec(
        script_id="ocr",
        path="test/test_ocr.py",
        description="Check Tesseract availability and language packs.",
    ),
    "owner_distribution": ScriptSpec(
        script_id="owner_distribution",
        path="test/test_owner_session_distribution.py",
        description="Inspect owner_session_id distribution in source + FAISS.",
    ),
    "owner_remap": ScriptSpec(
        script_id="owner_remap",
        path="test/test_owner_session_remap.py",
        description="Smoke test remap_owner_session_id dry-run command.",
    ),
    "api_smoke": ScriptSpec(
        script_id="api_smoke",
        path="test/test_api_smoke.py",
        description="Quick API smoke checks for status/chat/clear-memory.",
        requires_server=True,
    ),
    "stream_latency": ScriptSpec(
        script_id="stream_latency",
        path="test/benchmark_stream_latency.py",
        description="Benchmark SSE stream latency metrics.",
        requires_server=True,
    ),
    "retrieval_latency": ScriptSpec(
        script_id="retrieval_latency",
        path="test/benchmark_retrieval_latency.py",
        description="Benchmark retrieval latency by mode.",
        heavy=True,
    ),
    "chunk_strategy": ScriptSpec(
        script_id="chunk_strategy",
        path="test/test_chunk_strategy.py",
        description="Evaluate chunk size/overlap retrieval accuracy.",
        heavy=True,
    ),
    "ragas_pipeline": ScriptSpec(
        script_id="ragas_pipeline",
        path="test/test_ragas_pipeline.py",
        description="Run self-rag calibration pipeline (optional ragas).",
        heavy=True,
    ),
}


QUICK_SUITE = ["ocr", "owner_distribution", "owner_remap", "api_smoke"]
FULL_SUITE = [
    "ocr",
    "owner_distribution",
    "owner_remap",
    "api_smoke",
    "stream_latency",
    "retrieval_latency",
    "chunk_strategy",
    "ragas_pipeline",
]


def _parse_csv(raw: str) -> List[str]:
    items = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return items


def _is_server_reachable(base_url: str, timeout: float = 3.0) -> bool:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/status/", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def _build_command(spec: ScriptSpec, args) -> List[str]:
    cmd = [args.python, spec.path]

    if spec.script_id == "api_smoke":
        cmd.extend(["--base-url", args.base_url])
        if args.strict:
            cmd.append("--strict")

    if spec.script_id == "stream_latency":
        cmd.extend(
            [
                "--base-url",
                args.base_url,
                "--iterations",
                str(max(1, args.stream_iterations)),
                "--max-questions",
                str(max(1, args.stream_questions)),
                "--warmup",
                str(max(0, args.stream_warmup)),
                "--timeout",
                str(max(5.0, args.stream_timeout)),
            ]
        )

    if spec.script_id == "retrieval_latency":
        cmd.extend(["--iterations", "1", "--warmup", "0", "--max-questions", "5"])

    return cmd


def _resolve_suite_ids(args) -> List[str]:
    if args.only:
        requested = _parse_csv(args.only)
    elif args.suite == "full":
        requested = list(FULL_SUITE)
    else:
        requested = list(QUICK_SUITE)

    skipped = set(_parse_csv(args.skip))
    resolved: List[str] = []

    for script_id in requested:
        if script_id not in SCRIPT_SPECS:
            raise ValueError(f"unknown script id: {script_id}")
        if script_id in skipped:
            continue

        spec = SCRIPT_SPECS[script_id]
        if spec.heavy and not args.include_heavy:
            continue

        resolved.append(script_id)

    if not resolved:
        raise ValueError("no scripts selected after filters")

    return resolved


def _run_script(script_id: str, spec: ScriptSpec, args, *, server_up: bool) -> Dict[str, str]:
    if spec.requires_server and not server_up:
        return {
            "script": script_id,
            "status": "SKIPPED",
            "reason": "server_unreachable",
            "duration_s": "0.00",
        }

    command = _build_command(spec, args)
    started = time.perf_counter()

    proc = subprocess.run(
        command,
        cwd=str(args.backend_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=max(0, int(args.timeout_per_script)) or None,
    )

    elapsed = time.perf_counter() - started
    status = "PASS" if proc.returncode == 0 else "FAIL"
    reason = ""
    if status == "FAIL":
        reason = f"exit_code_{proc.returncode}"

    print(f"\n--- {script_id} ({status}) [{elapsed:.2f}s] ---")
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print("[stderr]")
        print(proc.stderr.strip())

    return {
        "script": script_id,
        "status": status,
        "reason": reason,
        "duration_s": f"{elapsed:.2f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backend utility scripts as a suite")
    parser.add_argument("--suite", choices=["quick", "full"], default="quick", help="Preset suite")
    parser.add_argument("--only", default="", help="Comma-separated script IDs")
    parser.add_argument("--skip", default="", help="Comma-separated script IDs to skip")
    parser.add_argument("--include-heavy", action="store_true", help="Include heavy scripts")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL for server-required scripts")
    parser.add_argument("--python", default=sys.executable, help="Python executable")
    parser.add_argument("--timeout-per-script", type=int, default=0, help="Timeout seconds per script (0 = no timeout)")
    parser.add_argument("--stream-iterations", type=int, default=1, help="Iterations for stream latency script")
    parser.add_argument("--stream-questions", type=int, default=3, help="Max questions for stream latency script")
    parser.add_argument("--stream-warmup", type=int, default=0, help="Warmup for stream latency script")
    parser.add_argument("--stream-timeout", type=float, default=45.0, help="HTTP timeout for stream latency script")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any script fails")

    args = parser.parse_args()
    args.backend_root = Path(__file__).resolve().parent.parent

    selected_ids = _resolve_suite_ids(args)
    server_up = _is_server_reachable(args.base_url)

    print("=== Backend Test Suite Runner ===")
    print(f"backend_root: {args.backend_root}")
    print(f"suite: {args.suite}")
    print(f"selected: {', '.join(selected_ids)}")
    print(f"server_reachable: {server_up}")

    results: List[Dict[str, str]] = []
    for script_id in selected_ids:
        spec = SCRIPT_SPECS[script_id]
        results.append(_run_script(script_id, spec, args, server_up=server_up))

    print("\n=== Summary ===")
    print("script | status | reason | duration_s")
    print("-" * 62)
    for row in results:
        print(
            f"{row['script']:<18} | {row['status']:<7} | "
            f"{row['reason'] or '-':<16} | {row['duration_s']:>9}"
        )

    failed = [row for row in results if row["status"] == "FAIL"]
    if failed and args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
