"""
ContextOS Text Chunker.

Splits documents into overlapping text chunks suitable for embedding
and vector storage, using LangChain's RecursiveCharacterTextSplitter.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 80
MIN_CHUNK_LENGTH = 30  # Minimum characters for a valid chunk


@dataclass
class Chunk:
    """
    Represents a text chunk ready for embedding and storage.

    Attributes:
        content: The text content of the chunk.
        metadata: Associated metadata (source, doc_id, etc.).
        chunk_index: Zero-based index of this chunk within the parent document.
        total_chunks: Total number of chunks from the parent document.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    total_chunks: int = 1


class TextChunker:
    """
    Text splitting utility using LangChain's RecursiveCharacterTextSplitter.

    Splits text into overlapping chunks with configurable size and overlap.
    Filters out chunks shorter than MIN_CHUNK_LENGTH characters and enriches
    each chunk's metadata with positional information.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """
        Initialize the TextChunker.

        Args:
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Number of overlapping characters between chunks.
        """
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        logger.info(
            "TextChunker initialized (size=%d, overlap=%d).",
            chunk_size,
            chunk_overlap,
        )

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """
        Split text into overlapping chunks with metadata.

        Splits the input text, filters out chunks shorter than MIN_CHUNK_LENGTH,
        and attaches metadata including chunk_index and total_chunks.

        Args:
            text: The text to split into chunks.
            metadata: Optional metadata dict to attach to each chunk.
                      Keys 'chunk_index' and 'total_chunks' will be added/overwritten.

        Returns:
            A list of Chunk dataclass instances, ordered by position.
        """
        if not text or not text.strip():
            logger.debug("Empty text provided to chunker, returning empty list.")
            return []

        base_metadata = metadata or {}

        # Split the text
        raw_splits = self._splitter.split_text(text)

        # Filter out short chunks
        valid_splits = [
            split for split in raw_splits
            if len(split.strip()) >= MIN_CHUNK_LENGTH
        ]

        if not valid_splits:
            logger.debug("No valid chunks after filtering (all too short).")
            return []

        total = len(valid_splits)

        chunks: list[Chunk] = []
        for idx, split_text in enumerate(valid_splits):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": idx,
                "total_chunks": total,
            }
            chunks.append(
                Chunk(
                    content=split_text.strip(),
                    metadata=chunk_metadata,
                    chunk_index=idx,
                    total_chunks=total,
                )
            )

        logger.debug(
            "Chunked text into %d chunks (from %d characters).",
            len(chunks),
            len(text),
        )
        return chunks

    def chunk_documents(
        self, documents: list[dict[str, Any]]
    ) -> list[Chunk]:
        """
        Chunk multiple documents at once.

        Args:
            documents: A list of document dicts, each having 'content' and 'metadata'.

        Returns:
            A flat list of Chunk instances from all documents.
        """
        all_chunks: list[Chunk] = []
        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_chunks = self.chunk(content, metadata)
            all_chunks.extend(doc_chunks)

        logger.info(
            "Chunked %d documents into %d total chunks.",
            len(documents),
            len(all_chunks),
        )
        return all_chunks
