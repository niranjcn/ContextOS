"""
ContextOS API Models.

Pydantic request and response models for all API endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---- Query Models ---- #

class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask ContextOS.",
        examples=["What did John discuss in last week's meeting?"],
    )


class QueryResponse(BaseModel):
    """Response body for the /query endpoint."""

    answer: str = Field(description="The generated answer.")
    sources: list[str] = Field(
        default_factory=list, description="Sources cited in the answer."
    )
    model_used: str = Field(description="The LLM model used for inference.")
    retrieval_time_ms: int = Field(description="Time spent on retrieval (ms).")
    inference_time_ms: int = Field(description="Time spent on inference (ms).")


# ---- Ingest Models ---- #

class IngestTextRequest(BaseModel):
    """Request body for the /ingest/text endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        description="The raw text content to ingest.",
    )
    doc_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this text.",
    )
    source: str = Field(
        default="direct_input",
        description="Source name for the ingested text.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to attach to the document.",
    )


class IngestResponse(BaseModel):
    """Response body for ingest operations."""

    doc_id: str = Field(description="The document ID that was ingested.")
    chunks_created: int = Field(description="Number of chunks created.")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities."
    )
    status: str = Field(description="Processing status.")


class IngestStatusResponse(BaseModel):
    """Response body for the /ingest/status endpoint."""

    total: int = Field(description="Total number of processed documents.")
    by_source: dict[str, int] = Field(
        default_factory=dict, description="Document count by source."
    )


# ---- Draft & Brief Models ---- #

class DraftRequest(BaseModel):
    """Request body for the /query/draft endpoint."""

    instruction: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="What to draft (e.g., 'Tell Priya the delivery is delayed').",
        examples=["Tell Priya the delivery is delayed by 2 weeks"],
    )
    recipient: str = Field(
        default="",
        description="Optional recipient name for context lookup.",
    )


class BriefRequest(BaseModel):
    """Request body for the /query/brief endpoint."""

    meeting_title: str = Field(
        ...,
        min_length=1,
        description="Title of the meeting.",
        examples=["Q4 Planning"],
    )
    attendees: list[str] = Field(
        ...,
        min_length=1,
        description="List of attendee names.",
        examples=[["Alice", "Bob", "Priya"]],
    )
    meeting_time: str = Field(
        default="",
        description="Optional meeting time string.",
    )


class DraftResponse(BaseModel):
    """Response body for the /query/draft endpoint."""

    draft: str = Field(description="The generated draft text.")
    context_used: list[str] = Field(
        default_factory=list, description="Sources used for context."
    )


class BriefResponse(BaseModel):
    """Response body for the /query/brief endpoint."""

    brief: str = Field(description="The generated meeting brief.")
    people_found: list[str] = Field(
        default_factory=list, description="People found in the knowledge graph."
    )


# ---- Graph Models ---- #

class PersonListResponse(BaseModel):
    """Response body for the /graph/people endpoint."""

    people: list[str] = Field(description="List of all person names.")
    count: int = Field(description="Total number of people.")


class DocumentResponse(BaseModel):
    """A single document in graph responses."""

    doc_id: str = Field(description="Document identifier.")
    title: str = Field(description="Document title.")
    source: str = Field(description="Source connector.")
    date: str = Field(description="Document date.")


class DocumentListResponse(BaseModel):
    """Response body for document list endpoints."""

    documents: list[DocumentResponse] = Field(
        default_factory=list, description="List of documents."
    )
    count: int = Field(description="Number of documents returned.")


class GraphStatsResponse(BaseModel):
    """Response body for the /graph/stats endpoint."""

    stats: dict[str, int] = Field(
        default_factory=dict, description="Node and relationship counts."
    )


# ---- Health Models ---- #

class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: str = Field(description="Overall system status.")
    ollama_running: bool = Field(description="Whether Ollama is reachable.")
    models_available: list[str] = Field(
        default_factory=list, description="Available Ollama models."
    )
    vector_count: int = Field(description="Number of vectors in the store.")
    graph_node_count: int = Field(
        description="Total number of nodes in the graph."
    )
    uptime_seconds: float = Field(description="Server uptime in seconds.")


class ModelsResponse(BaseModel):
    """Response body for the /health/models endpoint."""

    models: list[str] = Field(
        default_factory=list, description="Available model names."
    )


# ---- Generic Models ---- #

class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: str = Field(description="Error message.")
    status_code: int = Field(description="HTTP status code.")
