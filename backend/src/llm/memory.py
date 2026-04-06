"""Session conversation memory manager for RAG chats."""
import os
import re
import threading
import time
import uuid
from typing import Dict, List, Optional


class SessionMemoryStore:
    """In-memory bounded session history store with TTL eviction."""

    def __init__(self, history_max_messages: int, max_memory_sessions: int, session_ttl_seconds: int):
        self.history_max_messages = history_max_messages
        self.max_memory_sessions = max_memory_sessions
        self.session_ttl_seconds = session_ttl_seconds
        self._session_lock = threading.Lock()
        self._session_histories: Dict[str, List[Dict[str, str]]] = {}
        self._session_last_seen: Dict[str, float] = {}
        self._cache = None
        self._cache_sessions_key = "rag:session_memory:active"

        use_cache = str(os.getenv("USE_DJANGO_CACHE_MEMORY", "true")).strip().lower() in {"1", "true", "yes", "on"}
        if use_cache:
            try:
                from django.core.cache import cache

                self._cache = cache
            except Exception:
                self._cache = None

    def _cache_key(self, session_id: str) -> str:
        return f"rag:session_memory:{session_id}"

    def _cache_track_session(self, session_id: str) -> None:
        if self._cache is None:
            return

        active_sessions = self._cache.get(self._cache_sessions_key) or []
        if session_id in active_sessions:
            self._cache.set(self._cache_sessions_key, active_sessions, timeout=self.session_ttl_seconds)
            return

        active_sessions.append(session_id)
        if len(active_sessions) > self.max_memory_sessions:
            active_sessions = active_sessions[-self.max_memory_sessions :]
        self._cache.set(self._cache_sessions_key, active_sessions, timeout=self.session_ttl_seconds)

    def _cache_untrack_session(self, session_id: str) -> None:
        if self._cache is None:
            return

        active_sessions = self._cache.get(self._cache_sessions_key) or []
        if session_id not in active_sessions:
            return
        active_sessions = [item for item in active_sessions if item != session_id]
        self._cache.set(self._cache_sessions_key, active_sessions, timeout=self.session_ttl_seconds)

    def sanitize_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Normalize chat history into user/assistant message pairs with bounded size."""
        cleaned: List[Dict[str, str]] = []
        for item in history:
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                cleaned.append({"role": role, "content": content})

        return cleaned[-(self.history_max_messages * 2):]

    def normalize_session_id(self, session_id: Optional[str]) -> str:
        """Return a stable and safe session identifier for server-side memory."""
        normalized = str(session_id or "").strip()
        if not normalized:
            return uuid.uuid4().hex

        normalized = re.sub(r"[^A-Za-z0-9_-]", "", normalized)
        if len(normalized) > 128:
            normalized = normalized[:128]

        return normalized or uuid.uuid4().hex

    def _evict_stale_sessions(self) -> None:
        """Drop expired or oldest sessions to keep in-memory chat state bounded."""
        now = time.time()
        expired_session_ids = [
            sid
            for sid, last_seen in self._session_last_seen.items()
            if now - last_seen > self.session_ttl_seconds
        ]

        for sid in expired_session_ids:
            self._session_histories.pop(sid, None)
            self._session_last_seen.pop(sid, None)

        if len(self._session_histories) <= self.max_memory_sessions:
            return

        overflow = len(self._session_histories) - self.max_memory_sessions
        oldest_sessions = sorted(self._session_last_seen.items(), key=lambda item: item[1])[:overflow]
        for sid, _ in oldest_sessions:
            self._session_histories.pop(sid, None)
            self._session_last_seen.pop(sid, None)

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        if self._cache is not None:
            cached = self._cache.get(self._cache_key(session_id)) or []
            sanitized = self.sanitize_history(cached)
            self._cache.set(self._cache_key(session_id), sanitized, timeout=self.session_ttl_seconds)
            self._cache_track_session(session_id)
            return list(sanitized)

        with self._session_lock:
            self._evict_stale_sessions()
            history = self._session_histories.get(session_id, [])
            self._session_last_seen[session_id] = time.time()
            return list(history)

    def set_session_history(self, session_id: str, history: List[Dict[str, str]]) -> None:
        sanitized = self.sanitize_history(history)
        if self._cache is not None:
            self._cache.set(self._cache_key(session_id), sanitized, timeout=self.session_ttl_seconds)
            self._cache_track_session(session_id)
            return

        with self._session_lock:
            self._session_histories[session_id] = sanitized
            self._session_last_seen[session_id] = time.time()
            self._evict_stale_sessions()

    def append_session_messages(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        if not messages:
            return

        if self._cache is not None:
            existing = self._cache.get(self._cache_key(session_id)) or []
            merged = existing + messages
            self._cache.set(
                self._cache_key(session_id),
                self.sanitize_history(merged),
                timeout=self.session_ttl_seconds,
            )
            self._cache_track_session(session_id)
            return

        with self._session_lock:
            self._evict_stale_sessions()
            existing = self._session_histories.get(session_id, [])
            merged = existing + messages
            self._session_histories[session_id] = self.sanitize_history(merged)
            self._session_last_seen[session_id] = time.time()

    def clear_session_memory(self, session_id: str) -> bool:
        """Clear server-side conversation memory for one session id."""
        normalized_session_id = self.normalize_session_id(session_id)
        removed = False

        if self._cache is not None:
            removed = bool(self._cache.delete(self._cache_key(normalized_session_id)))
            self._cache_untrack_session(normalized_session_id)
            return removed

        with self._session_lock:
            if normalized_session_id in self._session_histories:
                self._session_histories.pop(normalized_session_id, None)
                removed = True
            if normalized_session_id in self._session_last_seen:
                self._session_last_seen.pop(normalized_session_id, None)
                removed = True

        return removed

    def active_sessions(self) -> int:
        if self._cache is not None:
            return len(self._cache.get(self._cache_sessions_key) or [])
        return len(self._session_histories)
