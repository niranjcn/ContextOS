"""Tests for core.ingestion.pipeline module."""

from pathlib import Path

import pytest


@pytest.fixture
def pipeline(tmp_db_dir: Path):
    """Create an IngestionPipeline with test stores."""
    from core.ingestion.pipeline import IngestionPipeline
    from core.storage.graph import GraphStore
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore

    metadata_store = MetadataStore(db_path=tmp_db_dir / "metadata" / "metadata.db")
    graph_store = GraphStore(db_path=tmp_db_dir / "graph")
    vector_store = VectorStore(db_path=tmp_db_dir / "vector")

    return IngestionPipeline(
        vector_store=vector_store,
        graph_store=graph_store,
        metadata_store=metadata_store,
    )


class TestProcessText:
    """Tests for IngestionPipeline.process_text."""

    def test_process_text_creates_chunks(self, pipeline):
        """process_text should create at least one chunk from non-trivial text."""
        result = pipeline.process_text(
            text=(
                "Barack Obama met with Google executives in New York. "
                "They discussed AI policy and its implications for the tech sector. "
                "The meeting took place on January 15th, 2024."
            ),
            doc_id="test_001",
            source="unit_test",
        )
        assert result["status"] == "success"
        assert result["chunks_created"] >= 1
        assert result["doc_id"] == "test_001"

    def test_process_text_extracts_entities(self, pipeline):
        """process_text should extract named entities from content."""
        result = pipeline.process_text(
            text="Barack Obama met with Google in New York on January 15th.",
            doc_id="test_002",
            source="unit_test",
        )
        entities = result.get("entities", {})
        # At minimum, one of people/organizations/locations should be populated
        has_entities = (
            len(entities.get("people", [])) > 0
            or len(entities.get("organizations", [])) > 0
            or len(entities.get("locations", [])) > 0
        )
        assert has_entities, f"Expected some entities, got: {entities}"

    def test_process_text_marks_processed(self, pipeline):
        """Processed document should be recorded in metadata store."""
        pipeline.process_text(
            text="Test content for metadata tracking.",
            doc_id="test_003",
            source="unit_test",
        )
        is_processed = pipeline._metadata_store.is_processed("test_003")
        assert is_processed

    def test_process_text_skips_duplicate(self, pipeline):
        """Ingesting the same doc_id twice should skip the second time."""
        result1 = pipeline.process_text(
            text="First ingestion of this document.",
            doc_id="test_004",
            source="unit_test",
        )
        result2 = pipeline.process_text(
            text="First ingestion of this document.",
            doc_id="test_004",
            source="unit_test",
        )
        assert result1["status"] == "success"
        assert result2["status"] == "skipped"


class TestIngestFile:
    """Tests for IngestionPipeline.ingest_file."""

    def test_ingest_txt_file(self, pipeline, tmp_path: Path):
        """ingest_file should process a .txt file successfully."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text(
            "Meeting notes from Q4 planning session with Alice and Bob. " "They decided to launch the new product in March.",
            encoding="utf-8",
        )

        result = pipeline.ingest_file(str(txt_file))
        assert result["status"] == "success"
        assert result["chunks_created"] >= 1

    def test_ingest_md_file(self, pipeline, tmp_path: Path):
        """ingest_file should process a .md file successfully."""
        md_file = tmp_path / "readme.md"
        md_file.write_text(
            "# Project Alpha\n\nThis project was started by John Smith "
            "at Acme Corp. The goal is to build an AI-powered assistant.",
            encoding="utf-8",
        )

        result = pipeline.ingest_file(str(md_file))
        assert result["status"] == "success"
        assert result["chunks_created"] >= 1

    def test_ingest_file_not_found(self, pipeline):
        """ingest_file should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            pipeline.ingest_file("/nonexistent/path/to/file.txt")

    def test_ingest_unsupported_format(self, pipeline, tmp_path: Path):
        """ingest_file should raise ValueError for unsupported extensions."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("col1,col2\nval1,val2", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported file type"):
            pipeline.ingest_file(str(csv_file))

    def test_ingest_empty_file_skipped(self, pipeline, tmp_path: Path):
        """ingest_file should skip an empty file gracefully."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        result = pipeline.ingest_file(str(empty_file))
        assert result["status"] == "skipped_empty"
        assert result["chunks_created"] == 0
