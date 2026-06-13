"""
ContextOS Test Fixtures.

Shared pytest fixtures for test database paths, mock settings,
pre-initialized stores, and sample data.
"""

import os
from pathlib import Path

import pytest

# Disable encryption for tests
os.environ["ENABLE_ENCRYPTION"] = "false"
os.environ["CONTEXTOS_ENCRYPTION_KEY"] = "test-key-for-unit-tests-only-32chars!"


@pytest.fixture
def tmp_db_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test databases."""
    db_dir = tmp_path / "test_db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


@pytest.fixture
def mock_settings(tmp_db_dir: Path):
    """Create a Settings-like object pointing to tmp dirs."""
    from core.config import Settings

    # Override env vars for testing
    os.environ["CONTEXTOS_DATA_DIR"] = str(tmp_db_dir / "data")
    os.environ["CONTEXTOS_DB_DIR"] = str(tmp_db_dir)
    os.environ["CONTEXTOS_LOG_DIR"] = str(tmp_db_dir / "logs")
    os.environ["ENABLE_ENCRYPTION"] = "false"

    return Settings()


@pytest.fixture
def metadata_store(tmp_db_dir: Path):
    """Provide an initialized MetadataStore with a test database."""
    from core.storage.metadata import MetadataStore

    db_path = tmp_db_dir / "metadata" / "metadata.db"
    return MetadataStore(db_path=db_path)


@pytest.fixture
def graph_store(tmp_db_dir: Path):
    """Provide an initialized GraphStore with test schema."""
    from core.storage.graph import GraphStore

    db_path = tmp_db_dir / "graph"
    return GraphStore(db_path=db_path)


@pytest.fixture
def vector_store(tmp_db_dir: Path):
    """Provide an initialized VectorStore."""
    from core.storage.vectors import VectorStore

    db_path = tmp_db_dir / "vector"
    return VectorStore(db_path=db_path)


@pytest.fixture
def sample_document() -> dict:
    """Return a sample document dict for testing."""
    return {
        "id": "test_doc_001",
        "source": "test_source",
        "content": (
            "Barack Obama met with executives from Google and Microsoft "
            "in New York on January 15th, 2024. They discussed artificial "
            "intelligence policy and its implications for the technology sector. "
            "The meeting was also attended by representatives from the United Nations."
        ),
        "metadata": {
            "title": "AI Policy Meeting Notes",
            "filename": "meeting_notes.txt",
            "author": "Test Author",
        },
        "created_at": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_entities():
    """Return a sample ExtractedEntities dataclass."""
    from core.ingestion.extractor import ExtractedEntities

    return ExtractedEntities(
        people=["Barack Obama"],
        organizations=["Google", "Microsoft", "United Nations"],
        dates=["January 15th, 2024"],
        locations=["New York"],
        topics=["artificial intelligence policy", "technology sector"],
    )
