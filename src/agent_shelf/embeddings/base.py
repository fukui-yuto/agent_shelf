"""Abstract embedding adapter interface."""

from __future__ import annotations

from typing import Protocol


class EmbeddingAdapter(Protocol):
    @property
    def dimension(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...
