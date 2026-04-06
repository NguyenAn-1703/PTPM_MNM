"""Validate remap_owner_session_id command via subprocess.

Usage:
    cd backend
    .venv/bin/python test/test_owner_session_remap.py --from-owner legacy --to-owner user123
    .venv/bin/python test/test_owner_session_remap.py --from-owner legacy --to-owner user123 --strict
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Tuple


def _run_remap_dry_run(backend_root: Path, from_owner: str, to_owner: str) -> Tuple[int, str, str]:
    cmd = [
        sys.executable,
        "manage.py",
        "remap_owner_session_id",
        "--from-owner",
        from_owner,
        "--to-owner",
        to_owner,
        "--dry-run",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(backend_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test remap_owner_session_id command")
    parser.add_argument("--from-owner", default="legacy", help="Source owner_session_id")
    parser.add_argument("--to-owner", default="legacy_tmp", help="Destination owner_session_id")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on failed assertions")

    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parent.parent
    code, stdout, stderr = _run_remap_dry_run(backend_root, args.from_owner, args.to_owner)

    print("=== remap_owner_session_id dry-run ===")
    print(stdout.strip() or "<no stdout>")
    if stderr.strip():
        print("\n[stderr]")
        print(stderr.strip())

    checks = {
        "exit_code_zero": code == 0,
        "contains_mode": "[DRY-RUN] remap owner_session_id" in stdout,
        "contains_source_line": "source_documents:" in stdout,
        "contains_vector_line": "faiss_docstore:" in stdout,
    }

    failed = [name for name, passed in checks.items() if not passed]

    print("\nChecks:")
    for name, passed in checks.items():
        print(f"- {name}: {'PASS' if passed else 'FAIL'}")

    if failed and args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
