"""RAG engine using ChromaDB."""

from __future__ import annotations

from pathlib import Path

import chromadb

from agent_shelf.embeddings.base import EmbeddingAdapter
from agent_shelf.rag.chunker import Chunk, split_text
from agent_shelf.rag.loader import load_documents


class RAGEngine:
    def __init__(
        self,
        agent_name: str,
        knowledge_dir: Path | None,
        embedding_adapter: EmbeddingAdapter,
        index_dir: Path | None = None,
    ) -> None:
        self._agent_name = agent_name
        self._knowledge_dir = knowledge_dir
        self._embedding = embedding_adapter

        persist_dir = index_dir or Path(f".agent_index/{agent_name}")
        persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=agent_name.replace("-", "_"),
            metadata={"hnsw:space": "cosine"},
        )

    def index(self) -> int:
        if self._knowledge_dir is None or not self._knowledge_dir.is_dir():
            return 0

        docs = load_documents(self._knowledge_dir)
        all_chunks: list[Chunk] = []
        for doc in docs:
            all_chunks.extend(split_text(doc.content, doc.source))

        if not all_chunks:
            return 0

        # Clear existing data and re-index
        existing = self._collection.get()
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            embeddings = self._embedding.embed(texts)
            ids = [f"{c.source}_{c.index}" for c in batch]
            metadatas = [{"source": c.source, "index": c.index} for c in batch]
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

        return len(all_chunks)

    def query(self, text: str, top_k: int = 5) -> list[dict[str, str]]:
        if self._collection.count() == 0:
            return []

        embedding = self._embedding.embed([text])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count()),
        )

        hits: list[dict[str, str]] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for doc, meta in zip(documents, metadatas):
            hits.append({"text": doc, "source": meta.get("source", "")})
        return hits
