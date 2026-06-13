"""Tests for core.ingestion.chunker module."""

import pytest

from core.ingestion.chunker import Chunk, TextChunker


@pytest.fixture
def chunker():
    """Create a TextChunker instance."""
    return TextChunker(chunk_size=100, chunk_overlap=20)


class TestTextChunker:
    """Tests for the TextChunker class."""

    def test_chunk_basic(self, chunker):
        """Should split text into multiple chunks."""
        text = "This is a test sentence. " * 20  # ~500 chars
        chunks = chunker.chunk(text, {"source": "test"})
        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_metadata(self, chunker):
        """Should include chunk_index and total_chunks in metadata."""
        text = "Testing metadata. " * 30
        chunks = chunker.chunk(text, {"source": "test", "doc_id": "d1"})
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks == len(chunks)
            assert chunk.metadata["source"] == "test"
            assert chunk.metadata["doc_id"] == "d1"

    def test_chunk_filters_short(self):
        """Should filter out chunks shorter than MIN_CHUNK_LENGTH."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "Short."
        chunks = chunker.chunk(text)
        # "Short." is 6 chars, below MIN_CHUNK_LENGTH of 30
        assert len(chunks) == 0

    def test_chunk_empty_string(self, chunker):
        """Empty string should return empty list."""
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_chunk_preserves_content(self, chunker):
        """All original text should appear across chunks."""
        text = "Hello world. " * 20
        chunks = chunker.chunk(text)
        combined = " ".join(c.content for c in chunks)
        # Due to overlap, some text repeats, but all original words should appear
        for word in ["Hello", "world"]:
            assert word in combined

    def test_chunk_documents(self, chunker):
        """chunk_documents should handle multiple docs."""
        docs = [
            {"content": "First document content. " * 10, "metadata": {"id": "1"}},
            {"content": "Second document content. " * 10, "metadata": {"id": "2"}},
        ]
        chunks = chunker.chunk_documents(docs)
        assert len(chunks) > 2  # Each doc should produce multiple chunks
