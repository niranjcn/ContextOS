"""
ContextOS Metadata Store.

SQLite-backed store for tracking processed document IDs, sync state,
and ingestion statistics. Prevents re-ingestion of already-processed documents.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# Constants
DEFAULT_DB_NAME = "metadata.db"
TABLE_NAME = "processed_documents"


class MetadataStore:
    """
    SQLite-backed metadata store for tracking document processing state.

    Tracks which documents have been ingested, their source connectors,
    and associated metadata. Used by connectors to skip already-processed
    documents during sync operations.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialize the MetadataStore.

        Args:
            db_path: Optional path to the SQLite database file.
                     Defaults to settings.get_db_path("metadata") / "metadata.db".
        """
        if db_path is None:
            db_path = settings.get_db_path("metadata") / DEFAULT_DB_NAME
        self._db_path = db_path
        self._init_db()
        logger.info("MetadataStore initialized at %s", self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection with row factory configured.

        Returns:
            A configured SQLite connection.
        """
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        """Create the processed_documents table if it doesn't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        try:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    doc_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{{}}',
                    processed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_source
                ON {TABLE_NAME}(source)
            """)
            conn.commit()
            logger.debug("Metadata database schema initialized.")
        except sqlite3.Error as exc:
            logger.error("Failed to initialize metadata DB: %s", exc)
            raise
        finally:
            conn.close()

    def mark_processed(
        self, doc_id: str, source: str, metadata: dict[str, Any]
    ) -> None:
        """
        Mark a document as processed.

        If the document ID already exists, updates the metadata and timestamp.

        Args:
            doc_id: Unique identifier for the document.
            source: The source connector name (e.g., 'local_files', 'gmail').
            metadata: Arbitrary metadata dict to store alongside the record.
        """
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata, default=str)
        conn = self._get_connection()
        try:
            conn.execute(
                f"""
                INSERT INTO {TABLE_NAME} (doc_id, source, metadata_json, processed_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (doc_id, source, metadata_json, now, now),
            )
            conn.commit()
            logger.debug("Marked document %s from %s as processed.", doc_id, source)
        except sqlite3.Error as exc:
            logger.error("Failed to mark document %s as processed: %s", doc_id, exc)
            raise
        finally:
            conn.close()

    def is_processed(self, doc_id: str) -> bool:
        """
        Check if a document has already been processed.

        Args:
            doc_id: The document ID to check.

        Returns:
            True if the document has been processed, False otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT 1 FROM {TABLE_NAME} WHERE doc_id = ?", (doc_id,)
            )
            result = cursor.fetchone() is not None
            return result
        except sqlite3.Error as exc:
            logger.error("Failed to check processed status for %s: %s", doc_id, exc)
            return False
        finally:
            conn.close()

    def get_all_processed(self) -> list[dict[str, Any]]:
        """
        Get all processed document records.

        Returns:
            A list of dicts with keys: doc_id, source, metadata, processed_at, updated_at.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT doc_id, source, metadata_json, processed_at, updated_at "
                f"FROM {TABLE_NAME} ORDER BY processed_at DESC"
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "doc_id": row["doc_id"],
                    "source": row["source"],
                    "metadata": json.loads(row["metadata_json"]),
                    "processed_at": row["processed_at"],
                    "updated_at": row["updated_at"],
                })
            return results
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve processed documents: %s", exc)
            return []
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """
        Get ingestion statistics grouped by source.

        Returns:
            A dict with 'total' count and 'by_source' breakdown.
            Example: {"total": 42, "by_source": {"local_files": 30, "gmail": 12}}
        """
        conn = self._get_connection()
        try:
            # Total count
            cursor = conn.execute(f"SELECT COUNT(*) as total FROM {TABLE_NAME}")
            total = cursor.fetchone()["total"]

            # Count by source
            cursor = conn.execute(
                f"SELECT source, COUNT(*) as count FROM {TABLE_NAME} GROUP BY source"
            )
            by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

            return {"total": total, "by_source": by_source}
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve stats: %s", exc)
            return {"total": 0, "by_source": {}}
        finally:
            conn.close()

    def remove(self, doc_id: str) -> bool:
        """
        Remove a processed document record.

        Args:
            doc_id: The document ID to remove.

        Returns:
            True if a record was removed, False if not found.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"DELETE FROM {TABLE_NAME} WHERE doc_id = ?", (doc_id,)
            )
            conn.commit()
            removed = cursor.rowcount > 0
            if removed:
                logger.debug("Removed processed record for %s.", doc_id)
            return removed
        except sqlite3.Error as exc:
            logger.error("Failed to remove document %s: %s", doc_id, exc)
            return False
        finally:
            conn.close()

    def close(self) -> None:
        """Close any open resources (no-op for per-call connections)."""
        logger.debug("MetadataStore closed.")
