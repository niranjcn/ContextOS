"""
ContextOS Base Connector.

Abstract base class for all data source connectors. Defines the interface
for fetching raw documents and syncing them into the ingestion pipeline.
"""

import abc
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BaseConnector(abc.ABC):
    """
    Abstract base class for ContextOS data source connectors.

    All connectors must implement `fetch()` and `validate_config()`.
    The `sync()` method orchestrates the fetch → deduplicate → ingest pipeline.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the base connector.

        Args:
            name: Human-readable name for this connector (e.g., 'local_files').
        """
        self.name = name
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @abc.abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch raw documents from the data source.

        Each returned dict must have these keys:
            - id (str): Unique identifier for the document.
            - source (str): Source connector name.
            - content (str): Full text content of the document.
            - metadata (dict): Arbitrary metadata (filename, author, etc.).
            - created_at (str): ISO format timestamp of creation/modification.

        Returns:
            A list of document dicts ready for ingestion.
        """
        ...

    @abc.abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present and valid.

        Returns:
            True if configuration is valid and the connector can operate.
        """
        ...

    def sync(
        self,
        metadata_store: Any,
        pipeline: Any,
    ) -> dict[str, int]:
        """
        Synchronize data from this connector into the ingestion pipeline.

        Fetches documents, filters out already-processed ones via the
        metadata store, and passes new documents to the pipeline.

        Args:
            metadata_store: A MetadataStore instance for deduplication.
            pipeline: An IngestionPipeline instance for processing.

        Returns:
            A dict with counts: {'fetched': N, 'new': M, 'skipped': S, 'errors': E}
        """
        stats = {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

        if not self.validate_config():
            self._logger.error("Configuration validation failed for connector '%s'.", self.name)
            return stats

        self._logger.info("Starting sync for connector '%s'...", self.name)

        try:
            documents = self.fetch()
            stats["fetched"] = len(documents)
            self._logger.info("Fetched %d documents from '%s'.", len(documents), self.name)
        except Exception as exc:
            self._logger.error("Fetch failed for '%s': %s", self.name, exc)
            stats["errors"] = 1
            return stats

        for doc in documents:
            doc_id = doc.get("id", "")
            if not doc_id:
                self._logger.warning("Document missing 'id' field, skipping.")
                stats["errors"] += 1
                continue

            # Skip already-processed documents
            if metadata_store.is_processed(doc_id):
                self._logger.debug("Document %s already processed, skipping.", doc_id)
                stats["skipped"] += 1
                continue

            try:
                pipeline.process_document(doc)
                metadata_store.mark_processed(
                    doc_id=doc_id,
                    source=self.name,
                    metadata=doc.get("metadata", {}),
                )
                stats["new"] += 1
            except Exception as exc:
                self._logger.error("Failed to process document %s: %s", doc_id, exc)
                stats["errors"] += 1

        self._logger.info(
            "Sync complete for '%s': %d fetched, %d new, %d skipped, %d errors.",
            self.name,
            stats["fetched"],
            stats["new"],
            stats["skipped"],
            stats["errors"],
        )
        return stats
