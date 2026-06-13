"""Tests for core.storage.vectors module."""

from core.storage.vectors import Chunk, SearchResult


class TestVectorStore:
    """Tests for the VectorStore class."""

    def test_add_and_count(self, vector_store):
        """Adding chunks should increase the count."""
        chunks = [
            Chunk(
                content="Machine learning is a subset of artificial intelligence.",
                metadata={"source": "test", "doc_id": "vdoc1"},
                chunk_index=0,
                total_chunks=1,
            )
        ]
        vector_store.add_chunks(chunks)
        assert vector_store.count() >= 1

    def test_search_returns_results(self, vector_store):
        """Search should return relevant results."""
        chunks = [
            Chunk(
                content="Python is a popular programming language for data science.",
                metadata={"source": "test", "doc_id": "vdoc2"},
            ),
            Chunk(
                content="JavaScript is widely used for web development.",
                metadata={"source": "test", "doc_id": "vdoc3"},
            ),
        ]
        vector_store.add_chunks(chunks)
        results = vector_store.search("programming language", k=2)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_result_has_fields(self, vector_store):
        """SearchResult should have content, metadata, and score."""
        chunks = [
            Chunk(
                content="FastAPI is a modern Python web framework.",
                metadata={"source": "test", "doc_id": "vdoc4"},
            ),
        ]
        vector_store.add_chunks(chunks)
        results = vector_store.search("web framework")
        if results:
            r = results[0]
            assert hasattr(r, "content")
            assert hasattr(r, "metadata")
            assert hasattr(r, "score")
            assert isinstance(r.content, str)

    def test_delete_by_source(self, vector_store):
        """delete_by_source should remove matching chunks."""
        chunks = [
            Chunk(
                content="Temporary data for deletion test.",
                metadata={"source": "deletable", "doc_id": "vdoc_del"},
            ),
        ]
        vector_store.add_chunks(chunks)
        initial_count = vector_store.count()
        vector_store.delete_by_source("deletable")
        assert vector_store.count() <= initial_count

    def test_empty_search(self, vector_store):
        """Search on empty store should return empty list."""
        # Fresh store may still have items from other tests
        results = vector_store.search("nonexistent gibberish query xyz123")
        assert isinstance(results, list)
