"""Embedding provider adapter using local Ollama (embeddinggemma).

Contract:
- model_name: str
- dimensions: int (768 for embeddinggemma)
- embed_documents(texts: list[str]) -> list[list[float]]
- embed_query(question: str) -> list[float]
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Protocol

log = logging.getLogger(__name__)


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Ollama local embedding adapter for EmbeddingGemma (768 dimensions)."""

    def __init__(
        self,
        model_name: str = "embeddinggemma",
        base_url: str = "http://localhost:11434",
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.dimensions = self._detect_dimensions()
        log.info(
            "MyEmbedder initialized: model=%s, dimensions=%d, endpoint=%s",
            self.model_name,
            self.dimensions,
            self.base_url,
        )

    def _detect_dimensions(self) -> int:
        """Kiểm tra kết nối và tự động lấy số chiều vector (thực tế 768)."""
        test_vec = self.embed_query("probe dimensions")
        dim = len(test_vec)
        if dim == 0:
            raise RuntimeError(f"Failed to get embeddings from Ollama model '{self.model_name}'")
        return dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Nhúng danh sách văn bản theo batch với tiền tố Document chuẩn của Google."""
        if not texts:
            return []

        all_vectors: list[list[float]] = []
        total = len(texts)

        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            # Tiền tố chỉ dẫn Asymmetric Retrieval của Google DeepMind cho EmbeddingGemma
            formatted_batch = [f"title: Manifesto of the Communist Party | text: {t}" for t in batch]
            payload = json.dumps({"model": self.model_name, "input": formatted_batch}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    vectors = data.get("embeddings", [])
                    if len(vectors) != len(batch):
                        raise RuntimeError(
                            f"Expected {len(batch)} embeddings, received {len(vectors)}"
                        )
                    all_vectors.extend(vectors)
            except urllib.error.URLError as e:
                raise RuntimeError(
                    f"Ollama connection failed at {self.base_url}/api/embed: {e}. "
                    "Make sure Ollama is running (`ollama serve`)."
                ) from e

        return all_vectors

    def embed_query(self, question: str) -> list[float]:
        """Nhúng 1 câu truy vấn với tiền tố Query chuẩn của Google."""
        # Tiền tố chỉ dẫn Asymmetric Retrieval của Google DeepMind cho EmbeddingGemma
        formatted_query = f"task: search result | query: {question}"
        payload = json.dumps({"model": self.model_name, "input": formatted_query}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                vectors = data.get("embeddings", [])
                if not vectors or len(vectors) == 0:
                    raise RuntimeError("No embedding returned for query")
                return vectors[0]
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Ollama connection failed at {self.base_url}/api/embed: {e}. "
                "Make sure Ollama is running (`ollama serve`)."
            ) from e
