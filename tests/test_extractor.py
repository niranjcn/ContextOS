"""Tests for core.ingestion.extractor module."""

import pytest


@pytest.fixture
def extractor():
    """Create an EntityExtractor instance."""
    try:
        from core.ingestion.extractor import EntityExtractor
        return EntityExtractor()
    except OSError:
        pytest.skip("spaCy en_core_web_sm model not installed")


class TestEntityExtractor:
    """Tests for the EntityExtractor class."""

    def test_extract_person(self, extractor):
        """Should extract 'Barack Obama' as a person entity."""
        result = extractor.extract(
            "Barack Obama met with Google in New York"
        )
        # spaCy should recognize Barack Obama as PERSON
        people_lower = [p.lower() for p in result.people]
        assert any("obama" in p for p in people_lower), (
            f"Expected 'Barack Obama' in people, got: {result.people}"
        )

    def test_extract_organization(self, extractor):
        """Should extract organizations from text."""
        result = extractor.extract(
            "Barack Obama met with Google in New York"
        )
        orgs_lower = [o.lower() for o in result.organizations]
        assert any("google" in o for o in orgs_lower), (
            f"Expected 'Google' in organizations, got: {result.organizations}"
        )

    def test_extract_date(self, extractor):
        """Should extract date expressions."""
        result = extractor.extract(
            "The meeting is on Monday, January 15th"
        )
        assert len(result.dates) > 0, (
            f"Expected at least one date, got: {result.dates}"
        )

    def test_extract_location(self, extractor):
        """Should extract location entities."""
        result = extractor.extract(
            "Barack Obama met with Google in New York"
        )
        locations_lower = [loc.lower() for loc in result.locations]
        assert any("new york" in loc for loc in locations_lower), (
            f"Expected 'New York' in locations, got: {result.locations}"
        )

    def test_extract_empty_string(self, extractor):
        """Empty string should return empty entity lists."""
        result = extractor.extract("")
        assert result.people == []
        assert result.organizations == []
        assert result.dates == []
        assert result.locations == []
        assert result.topics == []

    def test_extract_topics(self, extractor):
        """Should extract noun chunk topics."""
        result = extractor.extract(
            "Machine learning and artificial intelligence are transforming "
            "the healthcare industry and financial technology sector."
        )
        assert len(result.topics) > 0, "Expected at least one topic"

    def test_batch_extract(self, extractor):
        """batch_extract should return consistent results."""
        texts = [
            "Barack Obama visited Paris",
            "Google announced new AI features",
        ]
        batch_results = extractor.batch_extract(texts)
        assert len(batch_results) == 2

        individual_results = [extractor.extract(t) for t in texts]

        # Both methods should find the same people
        for batch_r, ind_r in zip(batch_results, individual_results):
            assert set(batch_r.people) == set(ind_r.people)

    def test_deduplication(self, extractor):
        """Should deduplicate entity names."""
        result = extractor.extract(
            "Obama met Obama. Barack Obama said Obama was there."
        )
        # Should not have duplicates
        assert len(result.people) == len(set(result.people))
