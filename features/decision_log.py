"""
ContextOS Decision Log Feature.

Maintains a searchable history of decisions extracted from documents,
meetings, and emails. Tracks who made decisions, when, and the context.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from core.inference.retriever import HybridRetriever
from core.storage.vectors import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Represents a logged decision."""

    summary: str
    context: str = ""
    participants: list[str] = field(default_factory=list)
    date: str = ""
    source: str = ""
    tags: list[str] = field(default_factory=list)


class DecisionLog:
    """
    Searchable decision history extracted from the knowledge base.

    Queries the vector store and knowledge graph for decision-related
    content and presents it in a structured format.
    """

    def __init__(self, retriever: HybridRetriever, vector_store: VectorStore) -> None:
        self._retriever = retriever
        self._vector_store = vector_store
        logger.info("DecisionLog initialized.")

    def search_decisions(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        """
        Search for decisions matching a query.

        Args:
            query: Search query about decisions.
            k: Maximum results to return.

        Returns:
            List of decision-related document excerpts.
        """
        search_query = f"decision decided agreed upon {query}"
        result = self._retriever.retrieve(search_query, k=k)

        decisions: list[dict[str, Any]] = []
        for chunk in result.semantic_chunks:
            decisions.append(
                {
                    "content": chunk.content,
                    "source": chunk.metadata.get("source", "unknown"),
                    "doc_id": chunk.metadata.get("doc_id", ""),
                    "score": chunk.score,
                    "related_people": result.mentioned_people,
                }
            )

        logger.info("Found %d decision-related results for '%s'.", len(decisions), query)
        return decisions

    def get_recent_decisions(self, k: int = 20) -> list[dict[str, Any]]:
        """
        Get recent decision-related content.

        Args:
            k: Maximum results to return.

        Returns:
            List of recent decision excerpts.
        """
        return self.search_decisions("recent decisions made", k=k)

    def get_decisions_by_person(self, name: str, k: int = 10) -> list[dict[str, Any]]:
        """
        Get decisions involving a specific person.

        Args:
            name: Person's name.
            k: Maximum results.

        Returns:
            List of decisions involving the person.
        """
        result = self._retriever.retrieve_for_person(name)
        decisions: list[dict[str, Any]] = []
        for chunk in result.semantic_chunks[:k]:
            content_lower = chunk.content.lower()
            if any(kw in content_lower for kw in ("decided", "agreed", "decision", "approved")):
                decisions.append(
                    {
                        "content": chunk.content,
                        "source": chunk.metadata.get("source", ""),
                        "person": name,
                    }
                )
        return decisions
