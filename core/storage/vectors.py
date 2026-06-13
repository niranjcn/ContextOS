"""
ContextOS Vector Store.

ChromaDB-backed vector database for semantic search over document chunks.
Uses HuggingFace sentence-transformers for embedding generation with
lazy initialization to avoid loading the model on import.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# Constants
COLLECTION_NAME = "contextos_chunks"
BATCH_SIZE = 100
DEFAULT_K = 5


@dataclass
class Chunk:
    """
    Represents a text chunk ready for embedding and storage.

    Attributes:
        content: The text content of the chunk.
        metadata: Associated metadata (source, doc_id, etc.).
        chunk_index: Index of this chunk within the parent document.
        total_chunks: Total number of chunks from the parent document.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    total_chunks: int = 1


@dataclass
class SearchResult:
    """
    Represents a single search result from the vector store.

    Attributes:
        content: The text content of the matching chunk.
        metadata: Associated metadata.
        score: Similarity score (lower is more similar for ChromaDB distances).
    """

    content: str
    metadata: dict[str, Any]
    score: float


class VectorStore:
    """
    ChromaDB-backed vector store for semantic search.

    Creates a persistent collection and provides methods for adding chunks,
    searching by similarity, and managing the store. The embedding model
    is lazily loaded on first use to avoid slow imports.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize the VectorStore.

        Args:
            db_path: Optional path to the ChromaDB persistence directory.
                     Defaults to settings.get_db_path("vector").
        """
        if db_path is None:
            db_path = settings.get_db_path("vector")
        self._db_path = db_path
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._embedding_fn = None  # Lazy-loaded
        self._client = None
        self._collection = None
        logger.info("VectorStore configured at %s", self._db_path)

    def _ensure_initialized(self) -> None:
        """Lazily initialize ChromaDB client, embedding function, and collection."""
        if self._collection is not None:
            return

        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self._client = chromadb.PersistentClient(path=str(self._db_path))

            # Use the sentence-transformers embedding function
            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=settings.EMBEDDING_MODEL)

            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "VectorStore initialized with collection '%s' (%d chunks).",
                COLLECTION_NAME,
                self._collection.count(),
            )
        except Exception as exc:
            logger.error("Failed to initialize VectorStore: %s", exc)
            raise

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """
        Add a list of chunks to the vector store in batches.

        Each chunk is embedded and stored with its metadata. Duplicate IDs
        are handled by ChromaDB's upsert behavior.

        Args:
            chunks: List of Chunk dataclass instances to add.
        """
        self._ensure_initialized()

        if not chunks:
            logger.debug("No chunks to add.")
            return

        total = len(chunks)
        added = 0

        for batch_start in range(0, total, BATCH_SIZE):
            batch = chunks[batch_start : batch_start + BATCH_SIZE]

            ids = []
            documents = []
            metadatas = []

            for chunk in batch:
                # Generate a deterministic ID from content hash and metadata
                chunk_id = self._generate_chunk_id(chunk)
                ids.append(chunk_id)
                documents.append(chunk.content)
                # ChromaDB requires string values in metadata
                clean_meta = self._sanitize_metadata(chunk.metadata)
                clean_meta["chunk_index"] = str(chunk.chunk_index)
                clean_meta["total_chunks"] = str(chunk.total_chunks)
                metadatas.append(clean_meta)

            try:
                self._collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                added += len(batch)
                logger.debug(
                    "Added batch %d-%d of %d chunks.",
                    batch_start,
                    batch_start + len(batch),
                    total,
                )
            except Exception as exc:
                logger.error(
                    "Failed to add chunk batch %d-%d: %s",
                    batch_start,
                    batch_start + len(batch),
                    exc,
                )

        logger.info("Added %d/%d chunks to vector store.", added, total)

    def search(self, query: str, k: int = DEFAULT_K) -> list[SearchResult]:
        """
        Search for chunks similar to the query string.

        Args:
            query: The search query text.
            k: Maximum number of results to return.

        Returns:
            A list of SearchResult instances ordered by similarity.
        """
        self._ensure_initialized()

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(k, self._collection.count() or k),
            )

            search_results = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {}
                    distance = results["distances"][0][i] if results["distances"] and results["distances"][0] else 0.0
                    search_results.append(
                        SearchResult(
                            content=doc,
                            metadata=metadata,
                            score=distance,
                        )
                    )

            logger.debug("Search returned %d results for query.", len(search_results))
            return search_results
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return []

    def delete_by_source(self, source: str) -> None:
        """
        Delete all chunks from a given source for re-ingestion.

        Args:
            source: The source identifier to delete chunks for.
        """
        self._ensure_initialized()

        try:
            self._collection.delete(where={"source": source})
            logger.info("Deleted chunks from source: %s", source)
        except Exception as exc:
            logger.error("Failed to delete chunks for source %s: %s", source, exc)

    def count(self) -> int:
        """
        Get the total number of chunks in the store.

        Returns:
            The count of stored chunks.
        """
        self._ensure_initialized()

        try:
            return self._collection.count()
        except Exception as exc:
            logger.error("Failed to get vector store count: %s", exc)
            return 0

    def _generate_chunk_id(self, chunk: Chunk) -> str:
        """
        Generate a deterministic ID for a chunk.

        Uses the source, doc_id, and chunk_index from metadata to create
        a stable identifier. Falls back to content hash if metadata is insufficient.

        Args:
            chunk: The chunk to generate an ID for.

        Returns:
            A string identifier for the chunk.
        """
        import hashlib

        source = chunk.metadata.get("source", "unknown")
        doc_id = chunk.metadata.get("doc_id", "")
        if doc_id:
            return f"{source}_{doc_id}_chunk{chunk.chunk_index}"
        # Fallback to content hash
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:12]
        return f"{source}_{content_hash}_chunk{chunk.chunk_index}"

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, str]:
        """
        Sanitize metadata for ChromaDB (all values must be str, int, float, or bool).

        Args:
            metadata: Raw metadata dict.

        Returns:
            A sanitized metadata dict with string values.
        """
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = ""
            else:
                sanitized[key] = str(value)
        return sanitized

    def close(self) -> None:
        """Close vector store resources."""
        logger.debug("VectorStore closed.")
