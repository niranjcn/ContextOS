"""
ContextOS Inference Engine.

Main query engine implementing the RAG (Retrieval-Augmented Generation) loop.
Retrieves context, builds prompts, and delegates generation to the configured
inference backend (Ollama, external CLI tool, etc.).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.inference.backends import InferenceBackend
from core.inference.prompt_builder import PromptBuilder
from core.inference.retriever import HybridRetriever, RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class EngineResponse:
    """
    Response from the ContextOS inference engine.

    Attributes:
        answer: The generated answer text.
        sources: List of source references cited in the answer.
        model_used: Name of the LLM model that generated the answer.
        retrieval_time_ms: Time spent on retrieval in milliseconds.
        inference_time_ms: Time spent on LLM inference in milliseconds.
    """

    answer: str = ""
    sources: list[str] = field(default_factory=list)
    model_used: str = ""
    retrieval_time_ms: int = 0
    inference_time_ms: int = 0


class ContextEngine:
    """
    Main query engine for ContextOS.

    Implements the RAG loop: retrieves relevant context from the knowledge
    graph and vector store, builds a structured prompt, and uses the configured
    inference backend for answer generation. Supports streaming responses.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        prompt_builder: PromptBuilder,
        backend: InferenceBackend,
    ) -> None:
        """
        Initialize the ContextEngine.

        Args:
            retriever: HybridRetriever instance for context retrieval.
            prompt_builder: PromptBuilder instance for prompt construction.
            backend: InferenceBackend for LLM generation.
        """
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._backend = backend
        logger.info("ContextEngine initialized (backend: %s).", backend.name())

    def query(self, question: str) -> EngineResponse:
        """
        Execute a RAG query: retrieve context, build prompt, and generate answer.

        Args:
            question: The natural language question to answer.

        Returns:
            An EngineResponse with the answer, sources, timing, and model info.
        """
        response = EngineResponse()

        # Step 1: Retrieval
        retrieval_start = time.perf_counter()
        try:
            retrieval = self._retriever.retrieve(question)
        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            retrieval = RetrievalResult()
        retrieval_end = time.perf_counter()
        response.retrieval_time_ms = int((retrieval_end - retrieval_start) * 1000)

        # Step 2: Build prompt
        prompt = self._prompt_builder.build(question, retrieval)

        # Step 3: LLM inference
        inference_start = time.perf_counter()
        try:
            answer = self._backend.generate(prompt)
            response.model_used = self._backend.name()
        except Exception as exc:
            logger.error("Inference failed: %s", exc)
            answer = (
                "I'm unable to generate a response right now. "
                "Please check that the inference backend is available. "
                f"Error: {exc}"
            )
            response.model_used = f"{self._backend.name()} (error)"

        inference_end = time.perf_counter()
        response.inference_time_ms = int((inference_end - inference_start) * 1000)
        response.answer = answer

        # Extract sources from retrieval
        source_set: set[str] = set()
        for chunk in retrieval.semantic_chunks:
            source = chunk.metadata.get("source", "")
            doc_id = chunk.metadata.get("doc_id", "")
            if source:
                source_set.add(f"{source}: {doc_id}" if doc_id else source)
        response.sources = sorted(source_set)

        logger.info(
            "Query completed in %dms retrieval + %dms inference (backend: %s).",
            response.retrieval_time_ms,
            response.inference_time_ms,
            response.model_used,
        )
        return response

    def query_stream(self, question: str) -> tuple[RetrievalResult, Any]:
        """
        Execute a streaming RAG query.

        Returns the retrieval result and a streaming generator from the backend.
        The caller is responsible for iterating over the generator.

        Args:
            question: The natural language question to answer.

        Returns:
            A tuple of (RetrievalResult, streaming_generator).
        """
        # Retrieval
        try:
            retrieval = self._retriever.retrieve(question)
        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            retrieval = RetrievalResult()

        # Build prompt
        prompt = self._prompt_builder.build(question, retrieval)

        # Create streaming response
        try:
            stream = self._backend.generate_stream(prompt)
            return retrieval, stream
        except Exception as exc:
            logger.error("Stream setup failed: %s", exc)
            raise RuntimeError(
                "All backends failed to generate a response."
            ) from exc

    def generate(self, prompt: str, model: str = "") -> str:
        """
        Generate a response from the inference backend.

        Sends a prompt directly to the configured backend, bypassing the RAG
        retrieval pipeline. Useful for features that do their own retrieval.

        Args:
            prompt: The full prompt to send to the backend.
            model: Ignored for external CLI backends; kept for compatibility.

        Returns:
            The generated response text.

        Raises:
            Exception: If the backend call fails.
        """
        return self._backend.generate(prompt)

    def is_ready(self) -> bool:
        """
        Check if the inference backend is ready.

        Returns:
            True if the backend is reachable and usable.
        """
        return self._backend.is_ready()

    def get_backend_info(self) -> dict[str, Any]:
        """
        Return metadata about the current inference backend.

        Returns:
            A dict with backend type, model, and availability info.
        """
        return self._backend.info()
