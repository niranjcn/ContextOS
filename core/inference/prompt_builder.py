"""
ContextOS Prompt Builder.

Constructs structured prompts for the LLM using retrieved context from
the knowledge graph and vector store. Supports general queries, smart
drafting, and meeting brief generation.
"""

import logging
from typing import Any

from core.inference.retriever import RetrievalResult

logger = logging.getLogger(__name__)

# ---- Prompt Templates ---- #

QUERY_PROMPT_TEMPLATE = """You are ContextOS, a private AI assistant with access to the user's professional knowledge base. Answer questions using ONLY the context provided below. If the context doesn't contain enough information, say so honestly.

## Your professional context
{graph_facts}

## Relevant documents
{semantic_chunks}

## Instructions
- Answer ONLY from the context provided above. Do not make up information.
- Cite your sources by referencing document names or sources when possible.
- Be specific and precise in your answers.
- If the context is insufficient, explain what information is missing.
- Keep your response concise but thorough.

## Question
{question}
"""

DRAFT_PROMPT_TEMPLATE = """You are helping draft content in the user's professional voice. Use the provided context and style examples to match their tone and communication patterns.

## Context
{context}

## Style Examples (match this tone and voice)
{style_examples}

## Drafting Instructions
{instruction}

Write the draft now, matching the user's voice and style:
"""

MEETING_BRIEF_TEMPLATE = """You are preparing a pre-meeting briefing for the user. Summarize all relevant context about the meeting participants and topics.

## Meeting Information
- Title: {meeting_title}
- Date: {meeting_date}
- Participants: {participants}
- Agenda: {agenda}

## Historical Context
{history}

## Instructions
Create a concise meeting brief that includes:
1. Key background on each participant and recent interactions
2. Relevant decisions or discussions from past meetings
3. Action items that may be outstanding
4. Suggested talking points based on the context

Meeting Brief:
"""


class PromptBuilder:
    """
    Constructs structured prompts for the ContextOS LLM.

    Uses pre-defined templates with clearly labeled sections for context,
    instructions, and questions. Supports general queries, smart drafting,
    and meeting brief generation.
    """

    def __init__(self) -> None:
        """Initialize the PromptBuilder."""
        logger.debug("PromptBuilder initialized.")

    def build(self, question: str, retrieval: RetrievalResult) -> str:
        """
        Build a context-aware prompt for a general query.

        Args:
            question: The user's question.
            retrieval: RetrievalResult from the hybrid retriever.

        Returns:
            A formatted prompt string ready for LLM inference.
        """
        # Format graph facts
        if retrieval.graph_facts:
            graph_facts = "\n".join(
                f"- {fact}" for fact in retrieval.graph_facts
            )
        else:
            graph_facts = "No specific relationship data available."

        # Format semantic chunks with source citations
        if retrieval.semantic_chunks:
            chunk_sections = []
            for i, chunk in enumerate(retrieval.semantic_chunks, 1):
                source = chunk.metadata.get("source", "unknown")
                doc_id = chunk.metadata.get("doc_id", "")
                citation = f"[Source: {source}"
                if doc_id:
                    citation += f", Doc: {doc_id}"
                citation += "]"

                chunk_sections.append(
                    f"### Document {i} {citation}\n{chunk.content}"
                )
            semantic_chunks = "\n\n".join(chunk_sections)
        else:
            semantic_chunks = "No relevant documents found."

        prompt = QUERY_PROMPT_TEMPLATE.format(
            graph_facts=graph_facts,
            semantic_chunks=semantic_chunks,
            question=question,
        )

        logger.debug(
            "Built query prompt (%d chars) with %d facts and %d chunks.",
            len(prompt),
            len(retrieval.graph_facts),
            len(retrieval.semantic_chunks),
        )
        return prompt

    def build_draft_prompt(
        self, instruction: str, context: str, style_examples: str
    ) -> str:
        """
        Build a prompt for smart draft generation.

        Args:
            instruction: What to draft (e.g., "Reply to the project update email").
            context: Relevant context about the topic.
            style_examples: Examples of the user's writing style.

        Returns:
            A formatted prompt string for drafting.
        """
        prompt = DRAFT_PROMPT_TEMPLATE.format(
            context=context or "No additional context available.",
            style_examples=style_examples or "No style examples provided.",
            instruction=instruction,
        )
        logger.debug("Built draft prompt (%d chars).", len(prompt))
        return prompt

    def build_brief_prompt(
        self, meeting_info: dict[str, Any], history: str
    ) -> str:
        """
        Build a prompt for pre-meeting briefing generation.

        Args:
            meeting_info: Dict with keys: title, date, participants, agenda.
            history: Historical context about participants and topics.

        Returns:
            A formatted prompt string for meeting brief generation.
        """
        participants = meeting_info.get("participants", [])
        if isinstance(participants, list):
            participants_str = ", ".join(participants)
        else:
            participants_str = str(participants)

        prompt = MEETING_BRIEF_TEMPLATE.format(
            meeting_title=meeting_info.get("title", "Untitled Meeting"),
            meeting_date=meeting_info.get("date", "Not specified"),
            participants=participants_str,
            agenda=meeting_info.get("agenda", "No agenda provided"),
            history=history or "No historical context available.",
        )
        logger.debug("Built meeting brief prompt (%d chars).", len(prompt))
        return prompt
