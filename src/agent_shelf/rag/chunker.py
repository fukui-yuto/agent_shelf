"""Text chunker for RAG indexing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    index: int


def split_text(
    text: str,
    source: str,
    max_chars: int = 1500,
    overlap_chars: int = 200,
) -> list[Chunk]:
    if len(text) <= max_chars:
        return [Chunk(text=text, source=source, index=0)]

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + max_chars
        chunk_text = text[start:end]
        chunks.append(Chunk(text=chunk_text, source=source, index=idx))
        start = end - overlap_chars
        idx += 1
    return chunks
