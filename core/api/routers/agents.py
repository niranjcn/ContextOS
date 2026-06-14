"""
ContextOS Agents Router.

Lists all available CLI agents/capabilities and their current status
for the dashboard to display and interact with.
"""

import logging

from fastapi import APIRouter

from core.api.models import AgentsListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "",
    response_model=AgentsListResponse,
    summary="List all available agents",
    description="Returns every CLI agent/capability with its availability status, description, and supported modes.",
)
async def list_agents() -> AgentsListResponse:
    """List all ContextOS agents and their readiness state."""
    from core.api.main import get_engine

    engine = get_engine()
    backend_ready = engine.is_ready() if engine else False
    backend_info = engine.get_backend_info() if engine else {}
    models = backend_info.get("models_available", [])

    agents = [
        {
            "id": "query",
            "name": "Query Agent",
            "description": "Ask natural language questions about your knowledge base and get context-aware answers with citations.",
            "icon": "search",
            "status": "ready" if backend_ready else "offline",
            "modes": ["ask"],
            "endpoint": "/query",
        },
        {
            "id": "draft",
            "name": "Draft Agent",
            "description": "Generate smart email drafts and messages in your writing voice using retrieved context.",
            "icon": "edit",
            "status": "ready" if backend_ready else "offline",
            "modes": ["draft"],
            "endpoint": "/query/draft",
        },
        {
            "id": "brief",
            "name": "Meeting Brief Agent",
            "description": "Generate pre-meeting briefing documents with context about each attendee from the knowledge graph.",
            "icon": "briefcase",
            "status": "ready" if backend_ready else "offline",
            "modes": ["brief"],
            "endpoint": "/query/brief",
        },
        {
            "id": "decisions",
            "name": "Decision Log Agent",
            "description": "Search past decisions, filter by person, or browse recent entries from the knowledge base.",
            "icon": "clipboard",
            "status": "ready" if backend_ready else "offline",
            "modes": ["search", "recent", "person"],
            "endpoint": "/query/decisions",
        },
        {
            "id": "ingest",
            "name": "Ingestion Agent",
            "description": "Ingest files, text, or documents into the knowledge base for indexing and retrieval.",
            "icon": "upload",
            "status": "ready",
            "modes": ["file", "text"],
            "endpoint": "/ingest",
        },
        {
            "id": "transcribe",
            "name": "Transcription Agent",
            "description": "Transcribe audio files using Whisper and automatically ingest the transcript into the knowledge base.",
            "icon": "mic",
            "status": "ready",
            "modes": ["audio"],
            "endpoint": "/transcribe",
        },
        {
            "id": "graph",
            "name": "Graph Explorer Agent",
            "description": "Explore the knowledge graph: browse people, documents, organizations, and their relationships.",
            "icon": "network",
            "status": "ready",
            "modes": ["people", "docs", "stats", "organizations"],
            "endpoint": "/graph",
        },
        {
            "id": "connectors",
            "name": "Connectors Agent",
            "description": "Configure and manage data source connectors: Gmail, Google Drive, local files, browser history.",
            "icon": "plug",
            "status": "ready",
            "modes": ["configure", "sync", "guide"],
            "endpoint": "/connectors",
        },
    ]

    return AgentsListResponse(
        agents=agents,
        total=len(agents),
        available=sum(1 for a in agents if a["status"] == "ready"),
        backend={
            "ready": backend_ready,
            "models": models,
        },
    )
