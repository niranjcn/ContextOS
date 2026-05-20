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

from core.api.models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Simple in-memory rate limiting
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 10  # requests per window
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
    _request_counts[client_id] = [
        t for t in _request_counts[client_id] if t > window_start
    ]

    if len(_request_counts[client_id]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {_RATE_LIMIT_MAX} requests "
            f"per {_RATE_LIMIT_WINDOW} seconds.",
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
            detail="Ollama is not running or no models are available.",
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
            detail="Ollama is not running or no models are available.",
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
