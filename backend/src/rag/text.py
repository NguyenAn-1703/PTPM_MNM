"""Text normalization, chunking, and citation utilities for RAG."""
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_chunk_params(default_size: int, default_overlap: int, chunk_size: Optional[int], chunk_overlap: Optional[int]) -> Tuple[int, int]:
    """Validate and normalize chunk parameters before splitting."""
    size = default_size if chunk_size is None else int(chunk_size)
    overlap = default_overlap if chunk_overlap is None else int(chunk_overlap)

    size = max(1, size)
    overlap = max(0, overlap)
    if overlap >= size:
        overlap = max(0, size // 5)

    return size, overlap


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into overlapping chunks."""
    text = (text or "").strip()
    if not text:
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks: List[str] = []

    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += step

    return chunks


def split_text_with_offsets(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    base_offset: int = 0,
) -> List[Dict[str, Any]]:
    """Split text into chunks with character offsets relative to original source."""
    text = text or ""
    if not text.strip():
        return []

    step = max(1, chunk_size - chunk_overlap)

    chunks: List[Dict[str, Any]] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        raw_chunk = text[start:end]
        chunk = raw_chunk.strip()
        if chunk:
            left_trim = len(raw_chunk) - len(raw_chunk.lstrip())
            right_trim = len(raw_chunk) - len(raw_chunk.rstrip())
            chunk_start = start + left_trim
            chunk_end = end - right_trim

            chunks.append(
                {
                    "content": chunk,
                    "char_start": base_offset + chunk_start,
                    "char_end": base_offset + chunk_end,
                }
            )

        if end >= text_len:
            break
        start += step

    return chunks


def extract_highlights(content: str, answer: str) -> List[Dict[str, Any]]:
    """Pick up to two high-overlap sentences from context as citation highlights."""
    content = (content or "").strip()
    answer = (answer or "").strip()
    if not content or not answer:
        return []

    answer_tokens = {
        token
        for token in re.findall(r"[A-Za-zÀ-ỹ0-9]{4,}", answer.lower())
        if token not in {"không", "được", "những", "trong", "thông", "liên", "quan"}
    }
    if not answer_tokens:
        return []

    matches: List[Dict[str, Any]] = []
    for raw_sentence in re.split(r"(?<=[\.\!\?])\s+|\n+", content):
        sentence = raw_sentence.strip()
        if len(sentence) < 24:
            continue

        sentence_tokens = set(re.findall(r"[A-Za-zÀ-ỹ0-9]{4,}", sentence.lower()))
        overlap = len(answer_tokens.intersection(sentence_tokens))
        if overlap == 0:
            continue

        start = content.lower().find(sentence.lower())
        if start < 0:
            continue

        matches.append(
            {
                "text": sentence,
                "start": start,
                "end": start + len(sentence),
                "_score": overlap,
            }
        )

    matches.sort(key=lambda item: item.get("_score", 0), reverse=True)
    highlights: List[Dict[str, Any]] = []
    for item in matches[:2]:
        highlights.append(
            {
                "text": item["text"],
                "start": item["start"],
                "end": item["end"],
            }
        )

    return highlights


def build_citations(contexts: List[Dict[str, Any]], answer: str) -> List[Dict[str, Any]]:
    """Attach source location and highlight fragments for each retrieved context."""
    enriched: List[Dict[str, Any]] = []
    for ctx in contexts:
        metadata = ctx.get("metadata", {}) or {}
        page_number = metadata.get("page_number")
        char_start = metadata.get("char_start")
        char_end = metadata.get("char_end")

        source_location = {
            "page_start": page_number,
            "page_end": page_number,
            "char_start": char_start,
            "char_end": char_end,
        }

        enriched.append(
            {
                **ctx,
                "source_location": source_location,
                "highlights": extract_highlights(str(ctx.get("content", "")), answer),
            }
        )

    return enriched


def format_history(history: List[Dict[str, str]], history_max_messages: int, history_max_chars: int) -> str:
    """Format and truncate recent chat history."""
    if not history:
        return "Không có lịch sử hội thoại."

    filtered = []
    for item in history:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            filtered.append({"role": role, "content": content})

    if not filtered:
        return "Không có lịch sử hội thoại."

    recent = filtered[-history_max_messages:]

    lines = []
    for msg in recent:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{prefix}: {msg['content']}")

    history_text = "\n".join(lines)
    if len(history_text) > history_max_chars:
        history_text = history_text[-history_max_chars:]
        history_text = "..." + history_text

    return history_text
