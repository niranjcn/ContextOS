"""
ContextOS Entity Extractor.

Uses spaCy NLP to extract named entities (people, organizations, dates,
locations) and key topics (noun chunks) from text content.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Constants
MAX_TOPICS = 10
MIN_CHUNK_LENGTH = 3  # minimum noun chunk length to keep


@dataclass
class ExtractedEntities:
    """
    Container for entities extracted from text.

    Attributes:
        people: List of person names found in the text.
        organizations: List of organization names found in the text.
        dates: List of date expressions found in the text.
        locations: List of location names found in the text.
        topics: List of key topics (noun chunks) found in the text (max 10).
    """

    people: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


class EntityExtractor:
    """
    spaCy-based named entity and topic extractor.

    Loads the en_core_web_sm model on initialization and provides methods
    to extract structured entity information from text. Deduplicates and
    normalizes extracted entities.
    """

    def __init__(self) -> None:
        """
        Initialize the EntityExtractor by loading the spaCy model.

        Raises:
            OSError: If the en_core_web_sm model is not installed.
        """
        try:
            import spacy

            self._nlp = spacy.load("en_core_web_sm")
            logger.info("EntityExtractor initialized with spaCy en_core_web_sm.")
        except OSError:
            logger.error("spaCy model 'en_core_web_sm' not found. " "Install it with: python -m spacy download en_core_web_sm")
            raise

    def extract(self, text: str) -> ExtractedEntities:
        """
        Extract named entities and topics from a text string.

        Processes the text through the spaCy NLP pipeline, categorizes
        entities by type, extracts noun chunks as topics, and deduplicates
        and normalizes all results.

        Args:
            text: The input text to extract entities from.

        Returns:
            An ExtractedEntities dataclass with categorized entities.
        """
        if not text or not text.strip():
            return ExtractedEntities()

        try:
            doc = self._nlp(text)

            people: set[str] = set()
            organizations: set[str] = set()
            dates: set[str] = set()
            locations: set[str] = set()

            # Extract named entities by label
            for ent in doc.ents:
                normalized = ent.text.strip()
                if not normalized:
                    continue

                if ent.label_ == "PERSON":
                    # Title case for person names
                    people.add(normalized.title())
                elif ent.label_ == "ORG":
                    organizations.add(normalized)
                elif ent.label_ in ("DATE", "TIME"):
                    dates.add(normalized)
                elif ent.label_ in ("GPE", "LOC", "FAC"):
                    locations.add(normalized)

            # Extract topics from noun chunks
            topics: list[str] = []
            seen_topics: set[str] = set()
            for chunk in doc.noun_chunks:
                topic = chunk.text.strip().lower()
                if len(topic) >= MIN_CHUNK_LENGTH and topic not in seen_topics and not topic.startswith(("the ", "a ", "an ")):
                    seen_topics.add(topic)
                    topics.append(chunk.text.strip())
                    if len(topics) >= MAX_TOPICS:
                        break

            result = ExtractedEntities(
                people=sorted(people),
                organizations=sorted(organizations),
                dates=sorted(dates),
                locations=sorted(locations),
                topics=topics,
            )

            logger.debug(
                "Extracted %d people, %d orgs, %d dates, %d locations, %d topics.",
                len(result.people),
                len(result.organizations),
                len(result.dates),
                len(result.locations),
                len(result.topics),
            )
            return result

        except Exception as exc:
            logger.error("Entity extraction failed: %s", exc)
            return ExtractedEntities()

    def batch_extract(self, texts: list[str]) -> list[ExtractedEntities]:
        """
        Extract entities from multiple texts efficiently.

        Uses spaCy's pipe() method for batch processing, which is more
        efficient than processing texts individually.

        Args:
            texts: A list of text strings to extract entities from.

        Returns:
            A list of ExtractedEntities, one per input text.
        """
        if not texts:
            return []

        results: list[ExtractedEntities] = []

        try:
            # Use spaCy's pipe for batch processing
            docs = self._nlp.pipe(texts, batch_size=50)

            for doc in docs:
                people: set[str] = set()
                organizations: set[str] = set()
                dates: set[str] = set()
                locations: set[str] = set()

                for ent in doc.ents:
                    normalized = ent.text.strip()
                    if not normalized:
                        continue

                    if ent.label_ == "PERSON":
                        people.add(normalized.title())
                    elif ent.label_ == "ORG":
                        organizations.add(normalized)
                    elif ent.label_ in ("DATE", "TIME"):
                        dates.add(normalized)
                    elif ent.label_ in ("GPE", "LOC", "FAC"):
                        locations.add(normalized)

                topics: list[str] = []
                seen_topics: set[str] = set()
                for chunk in doc.noun_chunks:
                    topic = chunk.text.strip().lower()
                    if (
                        len(topic) >= MIN_CHUNK_LENGTH
                        and topic not in seen_topics
                        and not topic.startswith(("the ", "a ", "an "))
                    ):
                        seen_topics.add(topic)
                        topics.append(chunk.text.strip())
                        if len(topics) >= MAX_TOPICS:
                            break

                results.append(
                    ExtractedEntities(
                        people=sorted(people),
                        organizations=sorted(organizations),
                        dates=sorted(dates),
                        locations=sorted(locations),
                        topics=topics,
                    )
                )

            logger.info("Batch extracted entities from %d texts.", len(texts))
        except Exception as exc:
            logger.error("Batch extraction failed: %s", exc)
            # Return empty results for remaining texts
            while len(results) < len(texts):
                results.append(ExtractedEntities())

        return results
