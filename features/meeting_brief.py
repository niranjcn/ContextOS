"""
ContextOS Meeting Brief Feature.

Generates pre-meeting briefings by gathering context about participants,
topics, and past interactions from the knowledge graph.
"""

import logging

from core.config import settings
from core.inference.engine import ContextEngine, EngineResponse
from core.inference.prompt_builder import PromptBuilder
from core.inference.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class MeetingBrief:
    """
    Generates pre-meeting briefings using context from the knowledge graph.

    Gathers information about meeting participants, related documents,
    and past interactions to prepare a comprehensive brief.
    """

    def __init__(self, engine: ContextEngine, retriever: HybridRetriever) -> None:
        self._engine = engine
        self._retriever = retriever
        self._prompt_builder = PromptBuilder()
        logger.info("MeetingBrief initialized.")

    def generate_brief(
        self,
        title: str,
        participants: list[str],
        date: str = "",
        agenda: str = "",
    ) -> EngineResponse:
        """
        Generate a meeting briefing.

        Args:
            title: Meeting title.
            participants: List of participant names.
            date: Meeting date string.
            agenda: Meeting agenda text.

        Returns:
            EngineResponse with the generated brief.
        """
        # Gather context for each participant
        history_parts: list[str] = []
        for person in participants:
            person_result = self._retriever.retrieve_for_person(person)
            if person_result.graph_facts:
                history_parts.append(f"### {person}")
                history_parts.extend(f"- {fact}" for fact in person_result.graph_facts)
            if person_result.semantic_chunks:
                for chunk in person_result.semantic_chunks[:2]:
                    history_parts.append(f"  Context: {chunk.content[:200]}...")

        # Also retrieve context about the meeting topic
        if agenda:
            topic_result = self._retriever.retrieve(agenda, k=3)
            if topic_result.semantic_chunks:
                history_parts.append("### Topic Context")
                for chunk in topic_result.semantic_chunks:
                    history_parts.append(f"- {chunk.content[:200]}...")

        history = "\n".join(history_parts) or "No historical context available."

        meeting_info = {
            "title": title,
            "date": date,
            "participants": participants,
            "agenda": agenda,
        }

        prompt = self._prompt_builder.build_brief_prompt(meeting_info, history)

        try:
            answer = self._engine.generate(prompt, settings.OLLAMA_MODEL)
            return EngineResponse(
                answer=answer,
                sources=[],
                model_used=settings.OLLAMA_MODEL,
            )
        except Exception as exc:
            logger.error("Brief generation failed: %s", exc)
            return EngineResponse(answer=f"Brief generation failed: {exc}")
