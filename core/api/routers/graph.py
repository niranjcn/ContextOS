"""
ContextOS Graph Router.

Provides endpoints for exploring the knowledge graph — listing people,
documents, and graph statistics.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from core.api.models import (
    DocumentListResponse,
    DocumentResponse,
    GraphStatsResponse,
    PersonListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get(
    "/people",
    response_model=PersonListResponse,
    summary="List all people",
    description="Returns a list of all person entities in the knowledge graph.",
)
async def list_people() -> PersonListResponse:
    """List all people in the knowledge graph."""
    from core.api.main import get_graph_store

    graph_store = get_graph_store()
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not initialized.")

    try:
        people = graph_store.get_all_people()
        return PersonListResponse(people=people, count=len(people))
    except Exception as exc:
        logger.error("Failed to list people: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve people: {str(exc)}"
        )


@router.get(
    "/organizations",
    summary="List all organizations",
    description="Returns a list of all organization entities in the knowledge graph.",
)
async def list_organizations() -> dict:
    """List all organizations in the knowledge graph."""
    from core.api.main import get_graph_store

    graph_store = get_graph_store()
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not initialized.")

    try:
        results = graph_store.search_entities("")
        orgs = sorted(
            {r["name"] for r in results if r.get("type") == "Organization"}
        )
        return {"organizations": orgs, "count": len(orgs)}
    except Exception as exc:
        logger.error("Failed to list organizations: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve organizations: {str(exc)}",
        )


@router.get(
    "/people/{name}/documents",
    response_model=DocumentListResponse,
    summary="Documents mentioning a person",
    description="Returns documents where the specified person is mentioned.",
)
async def person_documents(name: str) -> DocumentListResponse:
    """Get all documents mentioning a specific person."""
    from core.api.main import get_graph_store

    graph_store = get_graph_store()
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not initialized.")

    try:
        docs = graph_store.get_documents_for_person(name)
        documents = [
            DocumentResponse(
                doc_id=d.get("doc_id", ""),
                title=d.get("title", ""),
                source=d.get("source", ""),
                date=d.get("date", ""),
            )
            for d in docs
        ]
        return DocumentListResponse(documents=documents, count=len(documents))
    except Exception as exc:
        logger.error("Failed to get documents for person '%s': %s", name, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(exc)}",
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="Recent documents",
    description="Returns the most recently indexed documents (paginated).",
)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100, description="Max documents to return"),
) -> DocumentListResponse:
    """List recent documents from the knowledge graph."""
    from core.api.main import get_graph_store

    graph_store = get_graph_store()
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not initialized.")

    try:
        docs = graph_store.get_recent_documents(limit=limit)
        documents = [
            DocumentResponse(
                doc_id=d.get("doc_id", ""),
                title=d.get("title", ""),
                source=d.get("source", ""),
                date=d.get("date", ""),
            )
            for d in docs
        ]
        return DocumentListResponse(documents=documents, count=len(documents))
    except Exception as exc:
        logger.error("Failed to list documents: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve documents: {str(exc)}"
        )


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Graph statistics",
    description="Returns counts of all node and relationship types in the graph.",
)
async def graph_stats() -> GraphStatsResponse:
    """Get knowledge graph statistics."""
    from core.api.main import get_graph_store

    graph_store = get_graph_store()
    if graph_store is None:
        raise HTTPException(status_code=503, detail="Graph store not initialized.")

    try:
        stats = graph_store.get_stats()
        return GraphStatsResponse(stats=stats)
    except Exception as exc:
        logger.error("Failed to get graph stats: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve stats: {str(exc)}"
        )
