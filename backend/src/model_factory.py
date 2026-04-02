"""Factories for embeddings and LLM client with process-local caching."""
from functools import lru_cache
import json
from typing import Any, Dict, Iterator

import requests

from .config import get_rag_settings


@lru_cache(maxsize=1)
def get_embeddings():
    from src.llm.embeddings import OllamaHTTPEmbeddings

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
        self.num_predict = cfg.llm_num_predict

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": self.num_predict,
            },
        }
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()

    def generate_stream(self, prompt: str, temperature: float = 0.2) -> Iterator[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": self.num_predict,
            },
        }

        with requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
            stream=True,
        ) as response:
            response.raise_for_status()

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                token = str(payload.get("response", ""))
                if token:
                    yield token

                if payload.get("done"):
                    break


@lru_cache(maxsize=1)
def get_llm_client() -> OllamaLLMClient:
    return OllamaLLMClient()
