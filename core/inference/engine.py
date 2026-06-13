"""
ContextOS Inference Engine.

Main query engine implementing the RAG (Retrieval-Augmented Generation) loop.
Retrieves context, builds prompts, and calls Ollama for local LLM inference
with automatic fallback to alternative models.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

import ollama

from core.config import settings
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
    graph and vector store, builds a structured prompt, and uses Ollama
    for local LLM inference. Supports model fallback and streaming responses.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        prompt_builder: PromptBuilder,
    ) -> None:
        """
        Initialize the ContextEngine.

        Args:
            retriever: HybridRetriever instance for context retrieval.
            prompt_builder: PromptBuilder instance for prompt construction.
        """
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._ollama_client = ollama.Client(host=settings.OLLAMA_HOST)
        logger.info("ContextEngine initialized (model: %s).", settings.OLLAMA_MODEL)

    def query(self, question: str) -> EngineResponse:
        """
        Execute a RAG query: retrieve context, build prompt, and generate answer.

        Tries the primary model first, then falls back to the fallback model
        if the primary fails. Times retrieval and inference separately.

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

        # Step 3: LLM inference with fallback
        inference_start = time.perf_counter()
        model = settings.OLLAMA_MODEL

        try:
            answer = self.generate(prompt, model)
            response.model_used = model
        except Exception as primary_exc:
            logger.warning(
                "Primary model '%s' failed: %s. Trying fallback...",
                model,
                primary_exc,
            )
            fallback_model = settings.OLLAMA_FALLBACK_MODEL
            try:
                answer = self.generate(prompt, fallback_model)
                response.model_used = fallback_model
            except Exception as fallback_exc:
                logger.error(
                    "Fallback model '%s' also failed: %s",
                    fallback_model,
                    fallback_exc,
                )
                answer = (
                    "I'm unable to generate a response right now. "
                    "Please check that Ollama is running and a model is available. "
                    f"Primary error: {primary_exc}"
                )
                response.model_used = "none"

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
            "Query completed in %dms retrieval + %dms inference (model: %s).",
            response.retrieval_time_ms,
            response.inference_time_ms,
            response.model_used,
        )
        return response

    def query_stream(
        self, question: str
    ) -> tuple[RetrievalResult, Any]:
        """
        Execute a streaming RAG query.

        Returns the retrieval result and an Ollama streaming generator.
        The caller is responsible for iterating over the stream.

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
        model = settings.OLLAMA_MODEL
        try:
            stream = self._ollama_client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"num_predict": 2048},
            )
            return retrieval, stream
        except Exception as primary_exc:
            logger.warning(
                "Primary model stream failed: %s. Trying fallback...", primary_exc
            )
            fallback = settings.OLLAMA_FALLBACK_MODEL
            try:
                stream = self._ollama_client.chat(
                    model=fallback,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    options={"num_predict": 2048},
                )
                return retrieval, stream
            except Exception as fallback_exc:
                logger.error(
                    "Fallback model '%s' stream also failed: %s",
                    fallback,
                    fallback_exc,
                )
                raise RuntimeError(
                    "All models failed to generate a response. "
                    "Please check that Ollama is running and a model is available."
                ) from fallback_exc

    def generate(self, prompt: str, model: str = "") -> str:
        """
        Generate a response from the LLM.

        Sends a prompt directly to Ollama, bypassing the RAG retrieval pipeline.
        Useful for features that do their own retrieval and want to call the LLM
        with a custom prompt.

        Args:
            prompt: The full prompt to send to the model.
            model: Optional model name. Defaults to the configured primary model.

        Returns:
            The generated response text.

        Raises:
            Exception: If the Ollama call fails.
        """
        model = model or settings.OLLAMA_MODEL
        response = self._ollama_client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 2048},
        )
        return response["message"]["content"]

    def is_ready(self) -> bool:
        """
        Check if the engine is ready (Ollama running and model available).

        Returns:
            True if Ollama is reachable and at least one model is available.
        """
        try:
            models_response = self._ollama_client.list()
            available = [
                m.get("name", m.get("model", ""))
                for m in models_response.get("models", [])
            ]
            primary_available = any(
                settings.OLLAMA_MODEL in name for name in available
            )
            fallback_available = any(
                settings.OLLAMA_FALLBACK_MODEL in name for name in available
            )

            if primary_available or fallback_available:
                logger.debug("Engine ready. Available models: %s", available)
                return True

            logger.warning(
                "Ollama running but no suitable models found. "
                "Available: %s, Need: %s or %s",
                available,
                settings.OLLAMA_MODEL,
                settings.OLLAMA_FALLBACK_MODEL,
            )
            return False
        except Exception as exc:
            logger.warning("Ollama not reachable: %s", exc)
            return False

    def get_available_models(self) -> list[str]:
        """
        List available Ollama models.

        Returns:
            A list of model name strings, or empty list if Ollama is unreachable.
        """
        try:
            models_response = self._ollama_client.list()
            return [
                m.get("name", m.get("model", ""))
                for m in models_response.get("models", [])
            ]
        except Exception as exc:
            logger.warning("Could not list Ollama models: %s", exc)
            return []
