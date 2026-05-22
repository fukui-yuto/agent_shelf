"""Embedding adapter factory."""

from __future__ import annotations

import os

from agent_shelf.embeddings.base import EmbeddingAdapter


def create_embedding_adapter(provider: str | None = None) -> EmbeddingAdapter:
    provider = (provider or os.environ.get("EMBEDDING_PROVIDER", "local")).lower()

    if provider == "local":
        from agent_shelf.embeddings.local import LocalEmbeddingAdapter
        return LocalEmbeddingAdapter()
    elif provider == "openai":
        from agent_shelf.embeddings.openai_embed import OpenAIEmbeddingAdapter
        return OpenAIEmbeddingAdapter()
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
