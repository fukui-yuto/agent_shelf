"""OpenAI embedding adapter."""

from __future__ import annotations

import os

import openai


class OpenAIEmbeddingAdapter:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY")
        )
        self._dimension = 1536

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
