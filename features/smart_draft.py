"""
ContextOS Smart Draft Feature.

Generates email drafts and written content in the user's voice
by analyzing their writing style from previously ingested documents.
"""

import logging

from core.inference.engine import ContextEngine, EngineResponse
from core.inference.prompt_builder import PromptBuilder
from core.inference.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class SmartDraft:
    """
    Generates drafts in the user's writing voice.

    Retrieves examples of the user's past writing style, combines
    them with the current context, and uses the LLM to generate
    content that matches their tone and patterns.
    """

    def __init__(self, engine: ContextEngine, retriever: HybridRetriever) -> None:
        self._engine = engine
        self._retriever = retriever
        self._prompt_builder = PromptBuilder()
        logger.info("SmartDraft initialized.")

    def draft_reply(self, original_message: str, instruction: str = "Write a professional reply") -> EngineResponse:
        """
        Draft a reply to a message in the user's voice.

        Args:
            original_message: The message to reply to.
            instruction: Drafting instructions.

        Returns:
            EngineResponse with the drafted reply.
        """
        # Retrieve style examples
        style_result = self._retriever.retrieve("examples of my writing style emails", k=3)
        style_text = "\n---\n".join(c.content for c in style_result.semantic_chunks) or "No style examples available."

        # Retrieve context about the topic
        context_result = self._retriever.retrieve(original_message, k=3)
        context_text = "\n---\n".join(c.content for c in context_result.semantic_chunks) or original_message

        prompt = self._prompt_builder.build_draft_prompt(
            instruction=f"{instruction}\n\nOriginal message:\n{original_message}",
            context=context_text,
            style_examples=style_text,
        )

        try:
            answer = self._engine.generate(prompt)
            return EngineResponse(
                answer=answer,
                sources=[],
                model_used=self._engine._backend.name(),
            )
        except Exception as exc:
            logger.error("Draft generation failed: %s", exc)
            return EngineResponse(answer=f"Draft generation failed: {exc}")

    def draft_content(self, topic: str, content_type: str = "email") -> EngineResponse:
        """
        Draft new content about a topic.

        Args:
            topic: The subject to write about.
            content_type: Type of content (email, memo, summary).

        Returns:
            EngineResponse with the drafted content.
        """
        context_result = self._retriever.retrieve(topic, k=5)
        context_text = "\n---\n".join(c.content for c in context_result.semantic_chunks) or "No additional context."

        prompt = self._prompt_builder.build_draft_prompt(
            instruction=f"Write a {content_type} about: {topic}",
            context=context_text,
            style_examples="Use a professional, clear tone.",
        )

        try:
            answer = self._engine.generate(prompt)
            return EngineResponse(
                answer=answer,
                sources=[c.metadata.get("source", "") for c in context_result.semantic_chunks],
                model_used=self._engine._backend.name(),
            )
        except Exception as exc:
            logger.error("Content draft failed: %s", exc)
            return EngineResponse(answer=f"Draft failed: {exc}")
