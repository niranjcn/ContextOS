"""
ContextOS Graph Store.

Kuzu-backed knowledge graph for storing entities (people, organizations,
documents, topics) and their relationships. Supports upsert semantics
and fuzzy entity search.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import kuzu

from core.config import settings

logger = logging.getLogger(__name__)

# Schema constants
NODE_TABLES = {
    "Person": "(name STRING, PRIMARY KEY(name))",
    "Organization": "(name STRING, PRIMARY KEY(name))",
    "Document": "(doc_id STRING, title STRING, source STRING, date STRING, PRIMARY KEY(doc_id))",
    "Topic": "(name STRING, PRIMARY KEY(name))",
}

REL_TABLES = {
    "MENTIONED_IN": ("Person", "Document", "()"),
    "WORKS_AT": ("Person", "Organization", "()"),
    "RELATES_TO": ("Topic", "Document", "()"),
    "ORG_MENTIONED_IN": ("Organization", "Document", "()"),
}


class GraphStore:
    """
    Kuzu graph database wrapper for the ContextOS knowledge graph.

    Manages entities (Person, Organization, Document, Topic) and their
    relationships. Supports upsert operations to prevent duplicates
    and provides query methods for graph traversal.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize the GraphStore.

        Args:
            db_path: Optional path to the Kuzu database directory.
                     Defaults to settings.get_db_path("graph").
        """
        if db_path is None:
            db_path = settings.get_db_path("graph")
        self._db_path = db_path
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(self._db_path))
        self._conn = kuzu.Connection(self._db)
        self._init_schema()
        logger.info("GraphStore initialized at %s", self._db_path)

    def _init_schema(self) -> None:
        """Create node and relationship tables if they don't exist."""
        try:
            # Create node tables
            for table_name, schema in NODE_TABLES.items():
                try:
                    self._conn.execute(
                        f"CREATE NODE TABLE IF NOT EXISTS {table_name} {schema}"
                    )
                except kuzu.RuntimeError as exc:
                    if "already exists" not in str(exc).lower():
                        logger.warning("Schema creation note for %s: %s", table_name, exc)

            # Create relationship tables
            for rel_name, (from_table, to_table, props) in REL_TABLES.items():
                try:
                    self._conn.execute(
                        f"CREATE REL TABLE IF NOT EXISTS {rel_name} "
                        f"(FROM {from_table} TO {to_table}, {props.strip('()')}) "
                        if props != "()"
                        else f"CREATE REL TABLE IF NOT EXISTS {rel_name} "
                        f"(FROM {from_table} TO {to_table})"
                    )
                except kuzu.RuntimeError as exc:
                    if "already exists" not in str(exc).lower():
                        logger.warning("Schema creation note for %s: %s", rel_name, exc)

            logger.debug("Graph schema initialized.")
        except Exception as exc:
            logger.error("Failed to initialize graph schema: %s", exc)
            raise

    def add_document(
        self, doc_id: str, title: str, source: str, date: str
    ) -> None:
        """
        Add a document node to the graph (upsert).

        Args:
            doc_id: Unique document identifier.
            title: Document title or filename.
            source: Source connector name.
            date: Date string (ISO format preferred).
        """
        try:
            self._conn.execute(
                "MERGE (d:Document {doc_id: $doc_id}) "
                "SET d.title = $title, d.source = $source, d.date = $date",
                parameters={
                    "doc_id": doc_id,
                    "title": title,
                    "source": source,
                    "date": date,
                },
            )
            logger.debug("Added/updated document: %s", doc_id)
        except Exception as exc:
            logger.error("Failed to add document %s: %s", doc_id, exc)

    def add_entity(self, entity_type: str, name: str) -> None:
        """
        Add an entity node to the graph (upsert — won't duplicate).

        Args:
            entity_type: One of 'Person', 'Organization', 'Topic'.
            name: The entity name.
        """
        if entity_type not in ("Person", "Organization", "Topic"):
            logger.warning("Unknown entity type: %s", entity_type)
            return

        try:
            self._conn.execute(
                f"MERGE (e:{entity_type} {{name: $name}})",
                parameters={"name": name},
            )
            logger.debug("Added/updated %s: %s", entity_type, name)
        except Exception as exc:
            logger.error("Failed to add %s '%s': %s", entity_type, name, exc)

    def link_entity_to_document(
        self, entity_type: str, name: str, doc_id: str
    ) -> None:
        """
        Create a relationship between an entity and a document.

        Uses MENTIONED_IN for Person, ORG_MENTIONED_IN for Organization,
        and RELATES_TO for Topic.

        Args:
            entity_type: One of 'Person', 'Organization', 'Topic'.
            name: The entity name.
            doc_id: The document ID to link to.
        """
        rel_map = {
            "Person": "MENTIONED_IN",
            "Organization": "ORG_MENTIONED_IN",
            "Topic": "RELATES_TO",
        }
        rel_name = rel_map.get(entity_type)
        if not rel_name:
            logger.warning("Cannot link unknown entity type: %s", entity_type)
            return

        try:
            self._conn.execute(
                f"MATCH (e:{entity_type} {{name: $name}}), "
                f"(d:Document {{doc_id: $doc_id}}) "
                f"MERGE (e)-[:{rel_name}]->(d)",
                parameters={"name": name, "doc_id": doc_id},
            )
            logger.debug("Linked %s '%s' to document %s", entity_type, name, doc_id)
        except Exception as exc:
            logger.error(
                "Failed to link %s '%s' to %s: %s", entity_type, name, doc_id, exc
            )

    def get_documents_for_person(self, name: str) -> list[dict[str, Any]]:
        """
        Get all documents where a person is mentioned.

        Args:
            name: The person's name to search for.

        Returns:
            A list of document dicts with keys: doc_id, title, source, date.
        """
        try:
            result = self._conn.execute(
                "MATCH (p:Person {name: $name})-[:MENTIONED_IN]->(d:Document) "
                "RETURN d.doc_id, d.title, d.source, d.date",
                parameters={"name": name},
            )
            documents = []
            while result.has_next():
                row = result.get_next()
                documents.append({
                    "doc_id": row[0],
                    "title": row[1],
                    "source": row[2],
                    "date": row[3],
                })
            return documents
        except Exception as exc:
            logger.error("Failed to get documents for person '%s': %s", name, exc)
            return []

    def get_all_people(self) -> list[str]:
        """
        Get a list of all person names in the graph.

        Returns:
            A sorted list of unique person names.
        """
        try:
            result = self._conn.execute(
                "MATCH (p:Person) RETURN p.name ORDER BY p.name"
            )
            people = []
            while result.has_next():
                row = result.get_next()
                people.append(row[0])
            return people
        except Exception as exc:
            logger.error("Failed to get all people: %s", exc)
            return []

    def get_recent_documents(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get the most recently added documents.

        Args:
            limit: Maximum number of documents to return.

        Returns:
            A list of document dicts ordered by date (newest first).
        """
        try:
            result = self._conn.execute(
                f"MATCH (d:Document) RETURN d.doc_id, d.title, d.source, d.date "
                f"ORDER BY d.date DESC LIMIT {limit}",
            )
            documents = []
            while result.has_next():
                row = result.get_next()
                documents.append({
                    "doc_id": row[0],
                    "title": row[1],
                    "source": row[2],
                    "date": row[3],
                })
            return documents
        except Exception as exc:
            logger.error("Failed to get recent documents: %s", exc)
            return []

    def search_entities(self, query: str) -> list[dict[str, Any]]:
        """
        Search for entities by name using case-insensitive substring matching.

        Args:
            query: The search query string.

        Returns:
            A list of dicts with keys: name, type.
        """
        results: list[dict[str, Any]] = []
        search_pattern = f"%{query}%"

        for entity_type in ("Person", "Organization", "Topic"):
            try:
                result = self._conn.execute(
                    f"MATCH (e:{entity_type}) WHERE e.name CONTAINS $query "
                    f"RETURN e.name",
                    parameters={"query": query},
                )
                while result.has_next():
                    row = result.get_next()
                    results.append({"name": row[0], "type": entity_type})
            except Exception as exc:
                logger.error(
                    "Failed to search %s entities for '%s': %s",
                    entity_type,
                    query,
                    exc,
                )

        return results

    def get_stats(self) -> dict[str, int]:
        """
        Get counts of all node and relationship types.

        Returns:
            A dict with node and relationship counts.
        """
        stats: dict[str, int] = {}
        for table_name in NODE_TABLES:
            try:
                result = self._conn.execute(
                    f"MATCH (n:{table_name}) RETURN COUNT(n)"
                )
                if result.has_next():
                    stats[f"{table_name}_count"] = result.get_next()[0]
            except Exception as exc:
                logger.error("Failed to count %s nodes: %s", table_name, exc)
                stats[f"{table_name}_count"] = 0

        for rel_name in REL_TABLES:
            try:
                result = self._conn.execute(
                    f"MATCH ()-[r:{rel_name}]->() RETURN COUNT(r)"
                )
                if result.has_next():
                    stats[f"{rel_name}_count"] = result.get_next()[0]
            except Exception as exc:
                logger.error("Failed to count %s rels: %s", rel_name, exc)
                stats[f"{rel_name}_count"] = 0

        return stats

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
            logger.info("GraphStore connection closed.")
        except Exception as exc:
            logger.error("Error closing GraphStore: %s", exc)
