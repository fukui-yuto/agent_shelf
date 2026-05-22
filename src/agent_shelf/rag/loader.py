"""Document loaders for knowledge/ directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}


@dataclass
class Document:
    content: str
    source: str  # relative path from knowledge/


def load_documents(knowledge_dir: Path) -> list[Document]:
    if not knowledge_dir.is_dir():
        return []
    docs: list[Document] = []
    for ext in SUPPORTED_EXTENSIONS:
        for filepath in knowledge_dir.rglob(f"*{ext}"):
            text = filepath.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            rel = filepath.relative_to(knowledge_dir)
            docs.append(Document(content=text, source=str(rel)))
    return docs
