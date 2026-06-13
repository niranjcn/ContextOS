"""
ContextOS Ingestion Pipeline.

Orchestrates the full ingestion flow: takes raw documents, extracts entities,
chunks text, stores in the vector and graph databases, and tracks metadata.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from core.ingestion.chunker import TextChunker
from core.ingestion.extractor import EntityExtractor
from core.storage.graph import GraphStore
from core.storage.metadata import MetadataStore
from core.storage.vectors import VectorStore

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the document ingestion pipeline.

    Flow: raw document → entity extraction → text chunking → vector storage
    → graph storage → metadata tracking.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore,
        metadata_store: MetadataStore,
        extractor: EntityExtractor | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        """
        Initialize the IngestionPipeline.

        Args:
            vector_store: VectorStore instance for chunk embeddings.
            graph_store: GraphStore instance for entity relationships.
            metadata_store: MetadataStore instance for tracking processed docs.
            extractor: Optional EntityExtractor instance. Created if not provided.
            chunker: Optional TextChunker instance. Created if not provided.
        """
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._metadata_store = metadata_store
        self._extractor = extractor or EntityExtractor()
        self._chunker = chunker or TextChunker()
        logger.info("IngestionPipeline initialized.")

    def process_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single document through the full ingestion pipeline.

        Steps:
            1. Validate document structure.
            2. Extract entities using spaCy.
            3. Chunk text using LangChain splitter.
            4. Store chunks in the vector store.
            5. Store entities and relationships in the graph.
            6. Mark document as processed in metadata store.

        Args:
            document: A dict with keys: id, source, content, metadata, created_at.

        Returns:
            A summary dict with processing statistics:
                - doc_id: The document ID.
                - chunks_created: Number of chunks stored.
                - entities: Extracted entity counts.
                - status: 'success' or 'error'.

        Raises:
            ValueError: If the document is missing required fields.
        """
        # Validate document structure
        doc_id = document.get("id")
        source = document.get("source", "unknown")
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        created_at = document.get("created_at", datetime.now(timezone.utc).isoformat())

        if not doc_id:
            raise ValueError("Document must have an 'id' field.")

        # Skip already-processed documents
        if self._metadata_store.is_processed(doc_id):
            logger.info("Document %s already processed, skipping.", doc_id)
            return {
                "doc_id": doc_id,
                "chunks_created": 0,
                "entities": {},
                "status": "skipped",
            }

        if not content or not content.strip():
            logger.warning("Document %s has empty content, skipping.", doc_id)
            return {
                "doc_id": doc_id,
                "chunks_created": 0,
                "entities": {},
                "status": "skipped_empty",
            }

        logger.info("Processing document: %s (source: %s)", doc_id, source)

        try:
            # Step 1: Extract entities
            entities = self._extractor.extract(content)
            logger.debug(
                "Extracted entities for %s: %d people, %d orgs, %d topics.",
                doc_id,
                len(entities.people),
                len(entities.organizations),
                len(entities.topics),
            )

            # Step 2: Chunk the text
            chunk_metadata = {
                "doc_id": doc_id,
                "source": source,
                "created_at": created_at,
                **{k: str(v) for k, v in metadata.items()},
            }
            chunks = self._chunker.chunk(content, chunk_metadata)
            logger.debug("Created %d chunks for document %s.", len(chunks), doc_id)

            # Step 3: Store chunks in vector store
            if chunks:
                self._vector_store.add_chunks(chunks)

            # Step 4: Store entities and relationships in graph
            title = metadata.get("title", metadata.get("filename", doc_id))
            self._graph_store.add_document(
                doc_id=doc_id,
                title=str(title),
                source=source,
                date=created_at,
            )

            # Add entities and link them to the document
            for person in entities.people:
                self._graph_store.add_entity("Person", person)
                self._graph_store.link_entity_to_document("Person", person, doc_id)

            for org in entities.organizations:
                self._graph_store.add_entity("Organization", org)
                self._graph_store.link_entity_to_document("Organization", org, doc_id)

            for topic in entities.topics:
                self._graph_store.add_entity("Topic", topic)
                self._graph_store.link_entity_to_document("Topic", topic, doc_id)

            # Step 5: Mark as processed
            self._metadata_store.mark_processed(
                doc_id=doc_id,
                source=source,
                metadata={
                    **metadata,
                    "chunks_created": len(chunks),
                    "entities_found": {
                        "people": len(entities.people),
                        "organizations": len(entities.organizations),
                        "topics": len(entities.topics),
                    },
                },
            )

            result = {
                "doc_id": doc_id,
                "chunks_created": len(chunks),
                "entities": {
                    "people": entities.people,
                    "organizations": entities.organizations,
                    "dates": entities.dates,
                    "locations": entities.locations,
                    "topics": entities.topics,
                },
                "status": "success",
            }
            logger.info(
                "Successfully processed document %s: %d chunks, %d entities.",
                doc_id,
                len(chunks),
                sum(len(entities.people) + len(entities.organizations) + len(entities.topics) for _ in [1]),
            )
            return result

        except Exception as exc:
            logger.error("Failed to process document %s: %s", doc_id, exc)
            return {
                "doc_id": doc_id,
                "chunks_created": 0,
                "entities": {},
                "status": "error",
                "error": str(exc),
            }

    def process_batch(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Process multiple documents through the pipeline.

        Args:
            documents: A list of document dicts.

        Returns:
            A list of processing result dicts, one per document.
        """
        results: list[dict[str, Any]] = []
        total = len(documents)
        success = 0
        errors = 0

        for idx, doc in enumerate(documents, 1):
            logger.info("Processing document %d/%d...", idx, total)
            result = self.process_document(doc)
            results.append(result)
            if result["status"] == "success":
                success += 1
            elif result["status"] == "error":
                errors += 1

        logger.info(
            "Batch processing complete: %d/%d successful, %d errors.",
            success,
            total,
            errors,
        )
        return results

    def process_text(
        self,
        text: str,
        doc_id: str,
        source: str = "direct_input",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method to ingest raw text directly.

        Args:
            text: The text content to ingest.
            doc_id: A unique identifier for this text.
            source: Source name (default: 'direct_input').
            metadata: Optional metadata dict.

        Returns:
            Processing result dict.
        """
        document = {
            "id": doc_id,
            "source": source,
            "content": text,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.process_document(document)

    def ingest_file(self, file_path: str) -> dict[str, Any]:
        """
        Ingest a file by detecting its type and extracting text content.

        Supports .txt, .md, .pdf, and .docx files. Uses pdfplumber for PDF
        extraction and python-docx for DOCX extraction, with fallback to
        raw text reading if those libraries are not available.

        Args:
            file_path: Path to the file to ingest.

        Returns:
            Processing result dict from process_text.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file type is unsupported.
        """
        import hashlib
        from pathlib import Path

        path = Path(file_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        supported = {".txt", ".md", ".pdf", ".docx"}
        if suffix not in supported:
            raise ValueError(f"Unsupported file type '{suffix}'. " f"Supported: {', '.join(sorted(supported))}")

        content = ""

        if suffix in (".txt", ".md"):
            content = path.read_text(encoding="utf-8", errors="replace")

        elif suffix == ".pdf":
            try:
                import pdfplumber

                with pdfplumber.open(str(path)) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                    content = "\n\n".join(pages)
            except ImportError:
                logger.warning("pdfplumber not installed. Falling back to raw text read for PDF.")
                content = path.read_text(encoding="utf-8", errors="replace")

        elif suffix == ".docx":
            try:
                import docx

                doc = docx.Document(str(path))
                content = "\n\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
            except ImportError:
                logger.warning("python-docx not installed. Falling back to raw text read for DOCX.")
                content = path.read_text(encoding="utf-8", errors="replace")

        if not content.strip():
            logger.warning("File %s has no extractable content.", path)
            return {
                "doc_id": "",
                "chunks_created": 0,
                "entities": {},
                "status": "skipped_empty",
            }

        # Generate stable ID from file path
        doc_id = f"file_{hashlib.sha256(str(path).encode()).hexdigest()[:16]}"

        return self.process_text(
            text=content,
            doc_id=doc_id,
            source="file_ingest",
            metadata={
                "filename": path.name,
                "filepath": str(path),
                "extension": suffix,
                "size_bytes": path.stat().st_size,
            },
        )
