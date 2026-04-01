"""Factories for embeddings and LLM client with process-local caching."""
from functools import lru_cache
from typing import Any, Dict

import requests

from .config import get_rag_settings


@lru_cache(maxsize=1)
def get_embeddings():
    from src.rag.embeddings import OllamaHTTPEmbeddings

    cfg = get_rag_settings()
    return OllamaHTTPEmbeddings(
        base_url=cfg.ollama_base_url,
        model=cfg.embedding_model,
        timeout=120,
    )


class OllamaLLMClient:
    def __init__(self) -> None:
        cfg = get_rag_settings()
        self.base_url = cfg.ollama_base_url
        self.model = cfg.llm_model
        self.timeout = 120

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()


@lru_cache(maxsize=1)
def get_llm_client() -> OllamaLLMClient:
    return OllamaLLMClient()
