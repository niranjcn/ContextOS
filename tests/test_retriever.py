"""Tests for core.inference.retriever module."""

from unittest.mock import MagicMock

import pytest

from core.storage.vectors import SearchResult


@pytest.fixture
def mock_graph_store():
    """Create a mock GraphStore."""
    store = MagicMock()
    store.get_documents_for_person.return_value = [
        {"doc_id": "doc1", "title": "Meeting Notes", "source": "test", "date": "2024-01-15"}
    ]
    store.search_entities.return_value = [{"name": "Google", "type": "Organization"}]
    store.get_all_people.return_value = ["John Doe"]
    return store


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore."""
    store = MagicMock()
    store.search.return_value = [
        SearchResult(
            content="John discussed the project timeline.",
            metadata={"source": "test", "doc_id": "doc1"},
            score=0.3,
        ),
    ]
    return store


class TestHybridRetriever:
    """Tests for the HybridRetriever class."""

    def test_retrieve_returns_result(self, mock_graph_store, mock_vector_store):
        """retrieve() should return a RetrievalResult."""
        from core.inference.retriever import HybridRetriever, RetrievalResult

        # Use a mock extractor to avoid spaCy dependency
        mock_extractor = MagicMock()
        from core.ingestion.extractor import ExtractedEntities

        mock_extractor.extract.return_value = ExtractedEntities(people=["John"], organizations=["Google"])

        retriever = HybridRetriever(mock_graph_store, mock_vector_store, extractor=mock_extractor)
        result = retriever.retrieve("What did John discuss?")

        assert isinstance(result, RetrievalResult)
        assert len(result.semantic_chunks) > 0

    def test_retrieve_calls_both_stores(self, mock_graph_store, mock_vector_store):
        """retrieve() should query both graph and vector stores."""
        from core.inference.retriever import HybridRetriever

        mock_extractor = MagicMock()
        from core.ingestion.extractor import ExtractedEntities

        mock_extractor.extract.return_value = ExtractedEntities(people=["John"])

        retriever = HybridRetriever(mock_graph_store, mock_vector_store, extractor=mock_extractor)
        retriever.retrieve("Tell me about John")

        mock_graph_store.get_documents_for_person.assert_called()
        mock_vector_store.search.assert_called()

    def test_retrieve_for_person(self, mock_graph_store, mock_vector_store):
        """retrieve_for_person() should focus on the specified person."""
        from core.inference.retriever import HybridRetriever

        retriever = HybridRetriever(mock_graph_store, mock_vector_store)
        result = retriever.retrieve_for_person("John Doe")

        assert "John Doe" in result.mentioned_people
        mock_graph_store.get_documents_for_person.assert_called_with("John Doe")

    def test_retrieve_handles_empty_results(self):
        """retrieve() should handle empty results gracefully."""
        from core.inference.retriever import HybridRetriever

        empty_graph = MagicMock()
        empty_graph.get_documents_for_person.return_value = []
        empty_graph.search_entities.return_value = []

        empty_vector = MagicMock()
        empty_vector.search.return_value = []

        mock_extractor = MagicMock()
        from core.ingestion.extractor import ExtractedEntities

        mock_extractor.extract.return_value = ExtractedEntities()

        retriever = HybridRetriever(empty_graph, empty_vector, extractor=mock_extractor)
        result = retriever.retrieve("random query")

        assert result.semantic_chunks == []
        assert result.graph_facts == []
