"""
ContextOS Hybrid Retriever.

Combines knowledge graph traversal with vector semantic search to provide
context-rich retrieval results. First extracts entities from the query,
then performs graph lookup, followed by vector search, and merges results.
"""

import logging
from dataclasses import dataclass, field

from core.ingestion.extractor import EntityExtractor
from core.storage.graph import GraphStore
from core.storage.vectors import SearchResult, VectorStore

logger = logging.getLogger(__name__)

# Constants
DEFAULT_K = 5


@dataclass
class RetrievalResult:
    """
    Combined retrieval result from graph and vector sources.

    Attributes:
        semantic_chunks: Search results from vector similarity search.
        graph_facts: Human-readable sentences derived from graph relationships.
        mentioned_people: People detected in the query or related documents.
        mentioned_docs: Document titles/IDs from graph traversal.
    """

    semantic_chunks: list[SearchResult] = field(default_factory=list)
    graph_facts: list[str] = field(default_factory=list)
    mentioned_people: list[str] = field(default_factory=list)
    mentioned_docs: list[str] = field(default_factory=list)


class HybridRetriever:
    """
    Hybrid retrieval engine combining graph traversal and vector search.

    Extracts entities from the query, finds related documents and facts
    in the knowledge graph, performs semantic search in the vector store,
    and merges both result sets into a unified RetrievalResult.
    """

    def __init__(
        self,
        graph_store: GraphStore,
        vector_store: VectorStore,
        extractor: EntityExtractor | None = None,
    ) -> None:
        """
        Initialize the HybridRetriever.

        Args:
            graph_store: GraphStore instance for entity/relationship lookup.
            vector_store: VectorStore instance for semantic search.
            extractor: Optional EntityExtractor. Created lazily if not provided.
        """
        self._graph_store = graph_store
        self._vector_store = vector_store
        self._extractor = extractor
        logger.info("HybridRetriever initialized.")

    def _get_extractor(self) -> EntityExtractor:
        """Lazily initialize the entity extractor."""
        if self._extractor is None:
            self._extractor = EntityExtractor()
        return self._extractor

    def retrieve(self, query: str, k: int = DEFAULT_K) -> RetrievalResult:
        """
        Perform hybrid retrieval combining graph and vector search.

        Steps:
            1. Extract entities from the query using spaCy.
            2. Look up entities in the knowledge graph for related facts.
            3. Perform vector similarity search.
            4. Merge and deduplicate results.

        Args:
            query: The natural language query string.
            k: Maximum number of semantic chunks to return.

        Returns:
            A RetrievalResult with semantic chunks, graph facts, and entity lists.
        """
        result = RetrievalResult()

        # Step 1: Extract entities from the query
        try:
            extractor = self._get_extractor()
            entities = extractor.extract(query)
            logger.debug(
                "Query entities: people=%s, orgs=%s, topics=%s",
                entities.people,
                entities.organizations,
                entities.topics,
            )
        except Exception as exc:
            logger.warning("Entity extraction from query failed: %s", exc)
            entities = None

        # Step 2: Graph lookup for extracted entities
        if entities:
            result.mentioned_people.extend(entities.people)

            # Look up documents for each person mentioned
            for person in entities.people:
                try:
                    docs = self._graph_store.get_documents_for_person(person)
                    for doc in docs:
                        fact = (
                            f"{person} is mentioned in '{doc.get('title', 'untitled')}' "
                            f"(source: {doc.get('source', 'unknown')}, "
                            f"date: {doc.get('date', 'unknown')})"
                        )
                        if fact not in result.graph_facts:
                            result.graph_facts.append(fact)
                        doc_title = doc.get("title", doc.get("doc_id", ""))
                        if doc_title and doc_title not in result.mentioned_docs:
                            result.mentioned_docs.append(doc_title)
                except Exception as exc:
                    logger.warning("Graph lookup failed for person '%s': %s", person, exc)

            # Search for organizations in the graph
            for org in entities.organizations:
                try:
                    entity_results = self._graph_store.search_entities(org)
                    for er in entity_results:
                        fact = f"Organization '{er.get('name', org)}' found in knowledge graph."
                        if fact not in result.graph_facts:
                            result.graph_facts.append(fact)
                except Exception as exc:
                    logger.warning("Graph lookup failed for org '%s': %s", org, exc)

        # Step 3: Vector similarity search
        try:
            semantic_results = self._vector_store.search(query, k=k)
            result.semantic_chunks.extend(semantic_results)
            logger.debug("Vector search returned %d chunks.", len(semantic_results))
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)

        # Step 4: Deduplicate semantic chunks by content
        seen_content: set[str] = set()
        unique_chunks: list[SearchResult] = []
        for chunk in result.semantic_chunks:
            content_key = chunk.content[:100]  # Use first 100 chars as key
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_chunks.append(chunk)
        result.semantic_chunks = unique_chunks

        logger.info(
            "Hybrid retrieval: %d chunks, %d facts, %d people, %d docs.",
            len(result.semantic_chunks),
            len(result.graph_facts),
            len(result.mentioned_people),
            len(result.mentioned_docs),
        )
        return result

    def retrieve_for_person(self, name: str) -> RetrievalResult:
        """
        Retrieve all information related to a specific person.

        Performs a targeted graph lookup for the person and supplements
        with a vector search using the person's name as query.

        Args:
            name: The person's name to look up.

        Returns:
            A RetrievalResult focused on the specified person.
        """
        result = RetrievalResult()
        result.mentioned_people = [name]

        # Graph lookup
        try:
            docs = self._graph_store.get_documents_for_person(name)
            for doc in docs:
                fact = (
                    f"{name} is mentioned in '{doc.get('title', 'untitled')}' "
                    f"(source: {doc.get('source', 'unknown')}, "
                    f"date: {doc.get('date', 'unknown')})"
                )
                result.graph_facts.append(fact)
                doc_title = doc.get("title", doc.get("doc_id", ""))
                if doc_title:
                    result.mentioned_docs.append(doc_title)
        except Exception as exc:
            logger.warning("Graph lookup for person '%s' failed: %s", name, exc)

        # Vector search for the person
        try:
            semantic_results = self._vector_store.search(name, k=DEFAULT_K)
            result.semantic_chunks.extend(semantic_results)
        except Exception as exc:
            logger.warning("Vector search for person '%s' failed: %s", name, exc)

        logger.info(
            "Person retrieval for '%s': %d chunks, %d facts.",
            name,
            len(result.semantic_chunks),
            len(result.graph_facts),
        )
        return result
