"""Shared time parsing helpers for retrieval filters."""
from datetime import datetime
from typing import Any, Optional


def parse_timestamp(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        pass

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return None
