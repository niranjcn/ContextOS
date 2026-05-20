"""Tests for core.storage.graph module."""

import pytest


class TestGraphStore:
    """Tests for the GraphStore class."""

    def test_add_and_get_document(self, graph_store):
        """add_document then get_recent_documents should return it."""
        graph_store.add_document(
            doc_id="doc_001",
            title="Test Document",
            source="test",
            date="2024-01-15",
        )
        docs = graph_store.get_recent_documents(limit=10)
        assert len(docs) >= 1
        assert any(d["doc_id"] == "doc_001" for d in docs)

    def test_add_entity_idempotent(self, graph_store):
        """add_entity called twice should not create duplicates."""
        graph_store.add_entity("Person", "John Doe")
        graph_store.add_entity("Person", "John Doe")
        people = graph_store.get_all_people()
        john_count = sum(1 for p in people if p == "John Doe")
        assert john_count == 1

    def test_link_entity_to_document(self, graph_store):
        """Linking a person to a document should be traversable."""
        graph_store.add_document("doc_002", "Meeting Notes", "test", "2024-01-15")
        graph_store.add_entity("Person", "Jane Smith")
        graph_store.link_entity_to_document("Person", "Jane Smith", "doc_002")

        docs = graph_store.get_documents_for_person("Jane Smith")
        assert len(docs) >= 1
        assert any(d["doc_id"] == "doc_002" for d in docs)

    def test_get_documents_for_person(self, graph_store):
        """Should return correct documents for a person."""
        graph_store.add_document("doc_003", "Report A", "test", "2024-02-01")
        graph_store.add_document("doc_004", "Report B", "test", "2024-02-02")
        graph_store.add_entity("Person", "Alice")
        graph_store.link_entity_to_document("Person", "Alice", "doc_003")
        graph_store.link_entity_to_document("Person", "Alice", "doc_004")

        docs = graph_store.get_documents_for_person("Alice")
        doc_ids = {d["doc_id"] for d in docs}
        assert "doc_003" in doc_ids
        assert "doc_004" in doc_ids

    def test_get_all_people(self, graph_store):
        """Should return all people added."""
        graph_store.add_entity("Person", "Person A")
        graph_store.add_entity("Person", "Person B")
        people = graph_store.get_all_people()
        assert "Person A" in people
        assert "Person B" in people

    def test_search_entities(self, graph_store):
        """Should find entities by substring search."""
        graph_store.add_entity("Person", "Alexander Hamilton")
        results = graph_store.search_entities("Hamilton")
        assert any(r["name"] == "Alexander Hamilton" for r in results)

    def test_get_stats(self, graph_store):
        """get_stats should return counts."""
        graph_store.add_entity("Person", "Stats Person")
        graph_store.add_document("stats_doc", "Stats Doc", "test", "2024-01-01")
        stats = graph_store.get_stats()
        assert isinstance(stats, dict)
        assert stats.get("Person_count", 0) >= 1

    def test_organization_entity(self, graph_store):
        """Should handle organization entities."""
        graph_store.add_entity("Organization", "Acme Corp")
        graph_store.add_document("doc_org", "Org Doc", "test", "2024-01-01")
        graph_store.link_entity_to_document("Organization", "Acme Corp", "doc_org")
        results = graph_store.search_entities("Acme")
        assert any(r["name"] == "Acme Corp" for r in results)
