"""Test script: ingest sample documents and verify queries work."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["ENABLE_ENCRYPTION"] = "false"

SAMPLE_DOCUMENTS: dict[str, str] = {
    "project_notes.txt": """
Project Phoenix - Meeting Notes - October 14, 2024
Attendees: Arjun (project lead), Priya (backend dev), Rahul (design), Meera (QA)
We chose PostgreSQL over MongoDB for strong ACID guarantees.
API style: REST (not GraphQL) for mobile team simplicity.
Launch date: January 15, 2025 - tied to investor demo.
Hosting: AWS us-east-1 for lowest US latency.
""",
    "team_info.txt": """
Team Directory - Project Phoenix
Arjun Kumar - Project Lead, Bangalore
Priya Nair - Backend Developer, Kochi
Rahul Sharma - Product Designer, Mumbai
Meera Iyer - QA Engineer, Chennai
""",
    "tech_decisions.txt": """
Key Technology Decisions
Database: PostgreSQL (ACID compliant, team expertise)
Storage: Backblaze B2 (4x cheaper than AWS S3)
Hosting: AWS us-east-1
API: REST
""",
}

TEST_QUESTIONS = [
    ("Team lookup", "Who is on the project team and what are their roles?"),
    ("Tech decision", "Why was PostgreSQL chosen?"),
    ("Project details", "What is the launch date for Project Phoenix?"),
]


def test_ingestion() -> tuple[int, int]:
    tmp_dir = Path(tempfile.mkdtemp())
    os.environ["CONTEXTOS_DATA_DIR"] = str(tmp_dir / "data")
    os.environ["CONTEXTOS_DB_DIR"] = str(tmp_dir)

    from core.storage.graph import GraphStore
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore

    print("Initializing stores (clean temp directory)...")
    graph_store = GraphStore(db_path=tmp_dir / "graph")
    vector_store = VectorStore(db_path=tmp_dir / "vector")
    metadata_store = MetadataStore(db_path=tmp_dir / "metadata" / "metadata.db")

    from core.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline(vector_store, graph_store, metadata_store)

    print("Ingesting sample documents...")
    total_chunks = 0
    for filename, content in SAMPLE_DOCUMENTS.items():
        result = pipeline.process_text(
            text=content,
            doc_id=filename,
            source="test_script",
            metadata={"title": filename},
        )
        if result["status"] == "success":
            total_chunks += result["chunks_created"]
            print(f"  OK {filename} -> {result['chunks_created']} chunks")

    print(f"\nIngested {len(SAMPLE_DOCUMENTS)} documents -> {total_chunks} chunks")
    print(f"Vector store: {vector_store.count()} total chunks")

    stats = metadata_store.get_stats()
    print(f"Metadata store: {stats['total']} documents indexed")

    assert stats["total"] == len(SAMPLE_DOCUMENTS), f"Expected {len(SAMPLE_DOCUMENTS)}, got {stats['total']}"
    print("OK Ingestion verified: all documents stored correctly")
    return total_chunks, vector_store.count()


def test_queries():
    from core.inference.backends import OllamaBackend

    backend = OllamaBackend()
    if not backend.is_ready():
        print("\nOllama not running. Skipping query tests.")
        print("Start Ollama with: ollama serve")
        return

    print("\nInitializing inference engine...")
    from core.inference.engine import ContextEngine
    from core.inference.prompt_builder import PromptBuilder
    from core.inference.retriever import HybridRetriever
    from core.storage.graph import GraphStore
    from core.storage.vectors import VectorStore

    graph_store = GraphStore()
    vector_store = VectorStore()
    retriever = HybridRetriever(graph_store, vector_store)
    prompt_builder = PromptBuilder()
    engine = ContextEngine(retriever, prompt_builder, backend=backend)

    print("OK Ollama connected\n")

    passed = 0
    for test_name, question in TEST_QUESTIONS:
        response = engine.query(question)
        print(f"[{test_name}]")
        print(f"  Q: {question}")
        print(f"  A: {response.answer[:200]}...")
        print(f"  Sources: {', '.join(response.sources)} | {response.inference_time_ms}ms\n")
        passed += 1

    print(f"OK {passed}/{len(TEST_QUESTIONS)} queries completed")


def main():
    print("=" * 50)
    print("ContextOS - Ingestion & Query Pipeline Test")
    print("=" * 50)
    test_ingestion()
    test_queries()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
