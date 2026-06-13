"""
ContextOS Health Router.

Provides health check endpoints for monitoring system status,
Ollama availability, and available models.
"""

import logging
import time

from fastapi import APIRouter

from core.api.models import HealthResponse, ModelsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Track server start time
_START_TIME = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="System health check",
    description="Returns overall system health including Ollama status, " "vector store count, and graph node count.",
)
async def health_check() -> HealthResponse:
    """
    Perform a comprehensive health check.

    Returns status of Ollama, available models, vector and graph counts,
    and server uptime.
    """
    from core.api.main import get_engine, get_graph_store, get_vector_store

    engine = get_engine()
    vector_store = get_vector_store()
    graph_store = get_graph_store()

    # Check Ollama
    ollama_running = False
    models_available: list[str] = []
    if engine:
        ollama_running = engine.is_ready()
        models_available = engine.get_available_models()

    # Vector count
    vector_count = 0
    if vector_store:
        try:
            vector_count = vector_store.count()
        except Exception as exc:
            logger.warning("Could not get vector count: %s", exc)

    # Graph node count
    graph_node_count = 0
    if graph_store:
        try:
            stats = graph_store.get_stats()
            graph_node_count = sum(v for k, v in stats.items() if k.endswith("_count") and "REL" not in k)
        except Exception as exc:
            logger.warning("Could not get graph stats: %s", exc)

    uptime = time.time() - _START_TIME

    status = "healthy" if ollama_running else "degraded"

    return HealthResponse(
        status=status,
        ollama_running=ollama_running,
        models_available=models_available,
        vector_count=vector_count,
        graph_node_count=graph_node_count,
        uptime_seconds=round(uptime, 2),
    )


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available models",
    description="Lists all Ollama models available for inference.",
)
async def list_models() -> ModelsResponse:
    """List available Ollama models."""
    from core.api.main import get_engine

    engine = get_engine()
    models: list[str] = []
    if engine:
        models = engine.get_available_models()

    return ModelsResponse(models=models)
