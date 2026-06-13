"""
ContextOS Query Router.

Provides endpoints for querying the ContextOS engine, including
standard and streaming responses with rate limiting.
"""

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core.api.models import (
    BriefRequest,
    BriefResponse,
    DraftRequest,
    DraftResponse,
    QueryRequest,
    QueryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Simple in-memory rate limiting
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 20  # requests per window
_request_counts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_id: str = "default") -> None:
    """
    Check and enforce rate limiting.

    Args:
        client_id: Identifier for the client (default for single-user).

    Raises:
        HTTPException: If rate limit is exceeded.
    """
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW

    # Clean old entries
    _request_counts[client_id] = [t for t in _request_counts[client_id] if t > window_start]

    if len(_request_counts[client_id]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {_RATE_LIMIT_MAX} requests " f"per {_RATE_LIMIT_WINDOW} seconds.",
        )

    _request_counts[client_id].append(now)


@router.post(
    "",
    response_model=QueryResponse,
    summary="Query ContextOS",
    description="Submit a natural language question and receive a context-aware answer.",
)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Process a query through the RAG engine.

    Validates the question, checks rate limits, retrieves context,
    and generates an answer using the local LLM.
    """
    from core.api.main import get_engine

    _check_rate_limit()

    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Engine not initialized. Please wait for startup to complete.",
        )

    if not engine.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Inference backend is not available.",
        )

    logger.info("Processing query: %s...", request.question[:50])

    try:
        result = engine.query(request.question)
        return QueryResponse(
            answer=result.answer,
            sources=result.sources,
            model_used=result.model_used,
            retrieval_time_ms=result.retrieval_time_ms,
            inference_time_ms=result.inference_time_ms,
        )
    except Exception as exc:
        logger.error("Query processing failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(exc)}",
        )


@router.post(
    "/stream",
    summary="Stream query response",
    description="Submit a query and receive a streaming response.",
)
async def query_stream(request: QueryRequest) -> StreamingResponse:
    """
    Process a query with streaming response.

    Returns a Server-Sent Events stream of the LLM output.
    """
    from core.api.main import get_engine

    _check_rate_limit()

    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Engine not initialized.",
        )

    if not engine.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Inference backend is not available.",
        )

    logger.info("Processing streaming query: %s...", request.question[:50])

    try:
        retrieval, stream = engine.query_stream(request.question)

        async def generate():
            """Generate streaming response chunks."""
            try:
                for chunk in stream:
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
            except Exception as exc:
                logger.error("Streaming error: %s", exc)
                yield f"\n\n[Error: {str(exc)}]"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
        )
    except Exception as exc:
        logger.error("Stream setup failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Streaming query failed: {str(exc)}",
        )


@router.post(
    "/draft",
    response_model=DraftResponse,
    summary="Draft content",
    description="Generate a draft email or message using context from your knowledge base.",
)
async def query_draft(request: DraftRequest) -> DraftResponse:
    """
    Generate a smart draft using retrieved context and user writing style.

    Uses the SmartDraft feature to produce content in the user's voice.
    """
    from core.api.main import get_engine

    _check_rate_limit()

    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Engine not initialized. Please wait for startup to complete.",
        )

    logger.info("Processing draft request: %s...", request.instruction[:50])

    try:
        from features.smart_draft import SmartDraft

        retriever = engine._retriever
        draft_engine = SmartDraft(engine, retriever)
        result = draft_engine.draft_content(
            topic=request.instruction,
            content_type="email",
        )
        context_sources = result.sources if result.sources else []
        return DraftResponse(
            draft=result.answer,
            context_used=context_sources,
        )
    except Exception as exc:
        logger.error("Draft generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Draft generation failed: {str(exc)}",
        )


@router.post(
    "/brief",
    response_model=BriefResponse,
    summary="Generate meeting brief",
    description="Generate a pre-meeting briefing using context about attendees and topics.",
)
async def query_brief(request: BriefRequest) -> BriefResponse:
    """
    Generate a meeting brief using knowledge graph context.

    Retrieves information about each attendee and the meeting topic
    to produce a comprehensive pre-meeting brief.
    """
    from core.api.main import get_engine

    _check_rate_limit()

    engine = get_engine()
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Engine not initialized. Please wait for startup to complete.",
        )

    logger.info(
        "Generating brief for '%s' with %d attendees.",
        request.meeting_title,
        len(request.attendees),
    )

    try:
        from features.meeting_brief import MeetingBrief

        retriever = engine._retriever
        brief_engine = MeetingBrief(engine, retriever)
        result = brief_engine.generate_brief(
            title=request.meeting_title,
            participants=request.attendees,
            date=request.meeting_time,
        )
        return BriefResponse(
            brief=result.answer,
            people_found=request.attendees,
        )
    except Exception as exc:
        logger.error("Brief generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Brief generation failed: {str(exc)}",
        )
