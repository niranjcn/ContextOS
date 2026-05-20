"""
ContextOS Local File Connector.

Watches a local directory for new or modified files and ingests them
into the pipeline. Supports .txt, .md, .pdf, and .docx file types.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import settings
from core.ingestion.base import BaseConnector

logger = logging.getLogger(__name__)

# Constants
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
POLL_INTERVAL_SECONDS = 60
MAX_FILE_SIZE_MB = 50


class LocalFileConnector(BaseConnector):
    """
    Watches a local directory for supported files and ingests them.

    Supports .txt, .md, .pdf, and .docx files. Uses polling to detect
    new or modified files by checking file modification times against
    previously processed records.
    """

    def __init__(
        self,
        watch_dir: Optional[Path] = None,
        poll_interval: int = POLL_INTERVAL_SECONDS,
    ) -> None:
        """
        Initialize the LocalFileConnector.

        Args:
            watch_dir: Directory to watch for files. Defaults to settings data dir.
            poll_interval: Seconds between polling checks.
        """
        super().__init__(name="local_files")
        self._watch_dir = watch_dir or settings.CONTEXTOS_DATA_DIR
        self._poll_interval = poll_interval
        self._logger.info("LocalFileConnector watching: %s", self._watch_dir)

    def validate_config(self) -> bool:
        """
        Check that the watch directory exists and is readable.

        Returns:
            True if the directory exists and is accessible.
        """
        if not self._watch_dir.exists():
            self._logger.warning(
                "Watch directory does not exist: %s. Creating it.", self._watch_dir
            )
            try:
                self._watch_dir.mkdir(parents=True, exist_ok=True)
                return True
            except OSError as exc:
                self._logger.error("Cannot create watch directory: %s", exc)
                return False

        if not self._watch_dir.is_dir():
            self._logger.error("Watch path is not a directory: %s", self._watch_dir)
            return False

        return True

    def fetch(self) -> list[dict[str, Any]]:
        """
        Scan the watch directory for supported files.

        Recursively walks the directory, reads file content using
        appropriate loaders, and returns document dicts.

        Returns:
            A list of document dicts with id, source, content, metadata, created_at.
        """
        documents: list[dict[str, Any]] = []

        if not self._watch_dir.exists():
            self._logger.warning("Watch directory missing: %s", self._watch_dir)
            return documents

        for file_path in self._watch_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                self._logger.warning(
                    "File too large (%.1f MB), skipping: %s",
                    file_size_mb,
                    file_path,
                )
                continue

            try:
                doc = self._read_file(file_path)
                if doc:
                    documents.append(doc)
            except Exception as exc:
                self._logger.error("Error reading file %s: %s", file_path, exc)

        self._logger.info(
            "Found %d supported files in %s.", len(documents), self._watch_dir
        )
        return documents

    def _read_file(self, file_path: Path) -> Optional[dict[str, Any]]:
        """
        Read a file and return a document dict.

        Uses plain text reading for .txt and .md, and LangChain loaders
        for .pdf and .docx when available.

        Args:
            file_path: Path to the file to read.

        Returns:
            A document dict, or None if the file cannot be read.
        """
        suffix = file_path.suffix.lower()
        content = ""

        if suffix in (".txt", ".md"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                self._logger.error("Cannot read text file %s: %s", file_path, exc)
                return None

        elif suffix == ".pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader

                loader = PyPDFLoader(str(file_path))
                pages = loader.load()
                content = "\n\n".join(page.page_content for page in pages)
            except ImportError:
                self._logger.warning(
                    "PyPDFLoader not available. Install langchain-community for PDF support."
                )
                return None
            except Exception as exc:
                self._logger.error("Cannot read PDF %s: %s", file_path, exc)
                return None

        elif suffix == ".docx":
            try:
                from langchain_community.document_loaders import Docx2txtLoader

                loader = Docx2txtLoader(str(file_path))
                docs = loader.load()
                content = "\n\n".join(doc.page_content for doc in docs)
            except ImportError:
                self._logger.warning(
                    "Docx2txtLoader not available. Install langchain-community for DOCX support."
                )
                return None
            except Exception as exc:
                self._logger.error("Cannot read DOCX %s: %s", file_path, exc)
                return None

        if not content.strip():
            self._logger.debug("File %s has no content, skipping.", file_path)
            return None

        # Generate stable document ID from path + modification time
        stat = file_path.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        id_string = f"{file_path.resolve()}:{stat.st_mtime}"
        doc_id = hashlib.sha256(id_string.encode()).hexdigest()[:16]

        return {
            "id": f"local_{doc_id}",
            "source": "local_files",
            "content": content,
            "metadata": {
                "filename": file_path.name,
                "filepath": str(file_path.resolve()),
                "extension": suffix,
                "size_bytes": stat.st_size,
                "modified_at": mod_time.isoformat(),
            },
            "created_at": mod_time.isoformat(),
        }

    def run_forever(
        self,
        metadata_store: Any = None,
        pipeline: Any = None,
    ) -> None:
        """
        Run the connector in daemon mode, polling for changes.

        Continuously monitors the watch directory and ingests new or
        modified files at the configured interval.

        Args:
            metadata_store: MetadataStore instance for deduplication.
            pipeline: IngestionPipeline instance for processing.
        """
        if metadata_store is None or pipeline is None:
            self._logger.error(
                "Both metadata_store and pipeline are required for daemon mode."
            )
            return

        self._logger.info(
            "Starting local file watcher (poll every %ds)...", self._poll_interval
        )

        try:
            while True:
                stats = self.sync(metadata_store=metadata_store, pipeline=pipeline)
                if stats["new"] > 0:
                    self._logger.info(
                        "Sync cycle: %d new files ingested.", stats["new"]
                    )
                else:
                    self._logger.debug("Sync cycle: no new files.")
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            self._logger.info("File watcher stopped by user.")
        except Exception as exc:
            self._logger.error("File watcher error: %s", exc)
            raise
