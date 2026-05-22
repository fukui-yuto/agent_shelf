"""Local embedding adapter using sentence-transformers."""

from __future__ import annotations

from sentence_transformers import SentenceTransformer


class LocalEmbeddingAdapter:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
