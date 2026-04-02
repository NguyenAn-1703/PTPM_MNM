"""Embedding clients for RAG pipeline."""
from typing import List

import requests
from langchain_core.embeddings import Embeddings


class OllamaHTTPEmbeddings(Embeddings):
    """Minimal embedding client compatible with LangChain FAISS interface."""

    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts,
        }

        # Prefer modern Ollama endpoint that accepts batch input.
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings
        except Exception:
            pass

        # Fallback to legacy single-input endpoint for compatibility.
        vectors: List[List[float]] = []
        for text in texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            vector = data.get("embedding")
            if not vector:
                raise RuntimeError("Ollama embedding response missing 'embedding'")
            vectors.append(vector)

        return vectors

    def embed_query(self, text: str) -> List[float]:
        vectors = self.embed_documents([text])
        if not vectors:
            raise RuntimeError("Failed to generate query embedding")
        return vectors[0]
