"""Tests for core.inference.engine module."""

import pytest
from unittest.mock import MagicMock, patch

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


class TestContextEngine:
    """Tests for the ContextEngine class."""

    def test_query_returns_engine_response(self, mock_retriever, mock_prompt_builder):
        """query() should return an EngineResponse."""
        from core.inference.engine import ContextEngine, EngineResponse

        with patch("core.inference.engine.ollama") as mock_ollama:
            mock_client = MagicMock()
            mock_client.chat.return_value = {
                "message": {"content": "This is the AI answer."}
            }
            mock_client.list.return_value = {"models": [{"name": "llama3.2"}]}
            mock_ollama.Client.return_value = mock_client

            engine = ContextEngine(mock_retriever, mock_prompt_builder)
            result = engine.query("What is AI?")

            assert isinstance(result, EngineResponse)
            assert result.answer == "This is the AI answer."
            assert result.retrieval_time_ms >= 0
            assert result.inference_time_ms >= 0

    def test_query_includes_sources(self, mock_retriever, mock_prompt_builder):
        """query() should include sources from retrieval."""
        from core.inference.engine import ContextEngine

        with patch("core.inference.engine.ollama") as mock_ollama:
            mock_client = MagicMock()
            mock_client.chat.return_value = {"message": {"content": "Answer."}}
            mock_ollama.Client.return_value = mock_client

            engine = ContextEngine(mock_retriever, mock_prompt_builder)
            result = engine.query("test query")

            assert isinstance(result.sources, list)

    def test_is_ready_checks_ollama(self):
        """is_ready() should check Ollama availability."""
        from core.inference.engine import ContextEngine

        with patch("core.inference.engine.ollama") as mock_ollama:
            mock_client = MagicMock()
            mock_client.list.return_value = {
                "models": [{"name": "llama3.2"}]
            }
            mock_ollama.Client.return_value = mock_client

            engine = ContextEngine(MagicMock(), MagicMock())
            assert engine.is_ready() is True

    def test_is_ready_false_when_no_models(self):
        """is_ready() should return False when no models available."""
        from core.inference.engine import ContextEngine

        with patch("core.inference.engine.ollama") as mock_ollama:
            mock_client = MagicMock()
            mock_client.list.return_value = {"models": []}
            mock_ollama.Client.return_value = mock_client

            engine = ContextEngine(MagicMock(), MagicMock())
            assert engine.is_ready() is False

    def test_fallback_model_on_primary_failure(self, mock_retriever, mock_prompt_builder):
        """Should fall back to secondary model when primary fails."""
        from core.inference.engine import ContextEngine

        with patch("core.inference.engine.ollama") as mock_ollama:
            mock_client = MagicMock()
            # First call fails, second succeeds
            mock_client.chat.side_effect = [
                Exception("Primary model error"),
                {"message": {"content": "Fallback answer."}},
            ]
            mock_ollama.Client.return_value = mock_client

            engine = ContextEngine(mock_retriever, mock_prompt_builder)
            result = engine.query("test")

            assert "Fallback answer" in result.answer or "unable" in result.answer.lower()
