"""Tests for core.inference.engine module."""

from unittest.mock import MagicMock, patch

import pytest

from core.inference.retriever import RetrievalResult
from core.storage.vectors import SearchResult


@pytest.fixture
def mock_retriever():
    """Create a mock HybridRetriever."""
    retriever = MagicMock()
    retriever.retrieve.return_value = RetrievalResult(
        semantic_chunks=[
            SearchResult(
                content="Test content about AI.",
                metadata={"source": "test", "doc_id": "doc1"},
                score=0.2,
            )
        ],
        graph_facts=["John mentioned in Meeting Notes"],
        mentioned_people=["John"],
        mentioned_docs=["Meeting Notes"],
    )
    return retriever


@pytest.fixture
def mock_prompt_builder():
    """Create a mock PromptBuilder."""
    builder = MagicMock()
    builder.build.return_value = "Test prompt with context"
    return builder


@pytest.fixture
def mock_backend():
    """Create a mock InferenceBackend."""
    from core.inference.backends import InferenceBackend

    backend = MagicMock(spec=InferenceBackend)
    backend.generate.return_value = "This is the AI answer."
    backend.name.return_value = "test/backend"
    backend.is_ready.return_value = True
    backend.info.return_value = {"type": "test", "tool": "mock"}
    return backend


class TestContextEngine:
    """Tests for the ContextEngine class."""

    def test_query_returns_engine_response(self, mock_retriever, mock_prompt_builder, mock_backend):
        """query() should return an EngineResponse."""
        from core.inference.engine import ContextEngine, EngineResponse

        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        result = engine.query("What is AI?")

        assert isinstance(result, EngineResponse)
        assert result.answer == "This is the AI answer."
        assert result.retrieval_time_ms >= 0
        assert result.inference_time_ms >= 0
        assert result.model_used == "test/backend"

    def test_query_includes_sources(self, mock_retriever, mock_prompt_builder, mock_backend):
        """query() should include sources from retrieval."""
        from core.inference.engine import ContextEngine

        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        result = engine.query("test query")

        assert isinstance(result.sources, list)
        assert "test: doc1" in result.sources

    def test_is_ready_delegates_to_backend(self, mock_retriever, mock_prompt_builder, mock_backend):
        """is_ready() should delegate to the backend."""
        from core.inference.engine import ContextEngine

        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        assert engine.is_ready() is True
        mock_backend.is_ready.assert_called_once()

    def test_is_ready_false_when_backend_unavailable(self, mock_retriever, mock_prompt_builder, mock_backend):
        """is_ready() should return False when backend is not available."""
        from core.inference.engine import ContextEngine

        mock_backend.is_ready.return_value = False
        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        assert engine.is_ready() is False

    def test_backend_error_falls_back_to_error_message(self, mock_retriever, mock_prompt_builder, mock_backend):
        """Should return error message when backend fails."""
        from core.inference.engine import ContextEngine

        mock_backend.generate.side_effect = RuntimeError("Backend is down")
        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        result = engine.query("test")

        assert "unable" in result.answer.lower() or "error" in result.answer.lower()

    def test_get_backend_info_returns_metadata(self, mock_retriever, mock_prompt_builder, mock_backend):
        """get_backend_info() should return backend metadata."""
        from core.inference.engine import ContextEngine

        engine = ContextEngine(mock_retriever, mock_prompt_builder, mock_backend)
        info = engine.get_backend_info()
        assert info["tool"] == "mock"
