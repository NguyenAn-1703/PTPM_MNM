"""Simple API smoke tests for local backend.

Usage:
    cd backend
    .venv/bin/python test/test_api_smoke.py
    .venv/bin/python test/test_api_smoke.py --base-url http://127.0.0.1:8000/api --strict

Notes:
- Script expects backend server is already running.
- It checks core routes with lightweight assertions.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"


class SmokeFailure(Exception):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _request_json(method: str, url: str, *, timeout: float, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = requests.request(
        method=method,
        url=url,
        json=payload,
        timeout=timeout,
    )
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"{method} {url} khong tra ve JSON hop le") from exc

    data["_status_code"] = response.status_code
    return data


def _run_checks(base_url: str, timeout: float) -> List[str]:
    checks: List[str] = []

    status_payload = _request_json("GET", f"{base_url}/status/", timeout=timeout)
    _assert(status_payload.get("_status_code") == 200, "status endpoint khong tra ve 200")
    _assert(bool(status_payload.get("success")), "status endpoint khong success")
    checks.append("GET /status -> 200 + success=true")

    chat_payload = _request_json(
        "POST",
        f"{base_url}/chat/",
        timeout=timeout,
        payload={"question": " ", "session_id": "smoke_session"},
    )
    _assert(chat_payload.get("_status_code") == 400, "chat invalid payload khong tra ve 400")
    _assert(chat_payload.get("error_code") == "CHAT_EMPTY_QUESTION", "chat invalid khong dung error_code")
    checks.append("POST /chat (invalid) -> 400 + CHAT_EMPTY_QUESTION")

    clear_payload = _request_json(
        "POST",
        f"{base_url}/chat/memory/clear/",
        timeout=timeout,
        payload={"session_id": ""},
    )
    _assert(clear_payload.get("_status_code") == 400, "clear memory invalid payload khong tra ve 400")
    _assert(clear_payload.get("error_code") == "SESSION_INVALID_ID", "clear memory invalid khong dung error_code")
    checks.append("POST /chat/memory/clear (invalid) -> 400 + SESSION_INVALID_ID")

    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight API smoke checks")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend API base URL")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any check fails",
    )

    args = parser.parse_args()

    print(f"Smoke testing API: {args.base_url}")

    try:
        checks = _run_checks(base_url=args.base_url.rstrip("/"), timeout=max(1.0, args.timeout))
    except Exception as exc:
        print(f"[FAIL] {exc}")
        if args.strict:
            sys.exit(1)
        return

    print("\nPassed checks:")
    for item in checks:
        print(f"- {item}")


if __name__ == "__main__":
    main()
