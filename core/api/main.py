"""
ContextOS FastAPI Application.

App factory that initializes all routers, middleware, storage backends,
and the inference engine. Provides lifecycle events for startup/shutdown.
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """
    Container for all application singletons.

    Initialized during the lifespan startup event and reset for testing.
    """

    engine: Optional[object] = None
    graph_store: Optional[object] = None
    vector_store: Optional[object] = None
    metadata_store: Optional[object] = None
    pipeline: Optional[object] = None


_context = AppContext()


def get_engine():
    """Get the ContextEngine singleton."""
    return _context.engine


def get_graph_store():
    """Get the GraphStore singleton."""
    return _context.graph_store


def get_vector_store():
    """Get the VectorStore singleton."""
    return _context.vector_store


def get_metadata_store():
    """Get the MetadataStore singleton."""
    return _context.metadata_store


def get_pipeline():
    """Get the IngestionPipeline singleton."""
    return _context.pipeline


def reset_context() -> None:
    """Reset all singletons (for testing)."""
    global _context
    _context = AppContext()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown.

    On startup:
        - Initializes storage backends (graph, vector, metadata).
        - Creates the ingestion pipeline.
        - Creates the inference engine.
        - Verifies Ollama connectivity.

    On shutdown:
        - Closes all database connections cleanly.
    """
    global _context

    logger.info("ContextOS starting up...")

    try:
        # Initialize storage backends
        from core.storage.graph import GraphStore
        from core.storage.metadata import MetadataStore
        from core.storage.vectors import VectorStore

        _context.metadata_store = MetadataStore()
        _context.graph_store = GraphStore()
        _context.vector_store = VectorStore()
        logger.info("Storage backends initialized.")

        # Initialize ingestion pipeline
        from core.ingestion.pipeline import IngestionPipeline

        _context.pipeline = IngestionPipeline(
            vector_store=_context.vector_store,
            graph_store=_context.graph_store,
            metadata_store=_context.metadata_store,
        )
        logger.info("Ingestion pipeline initialized.")

        # Initialize inference engine
        from core.inference.engine import ContextEngine
        from core.inference.prompt_builder import PromptBuilder
        from core.inference.retriever import HybridRetriever

        retriever = HybridRetriever(
            graph_store=_context.graph_store,
            vector_store=_context.vector_store,
        )
        prompt_builder = PromptBuilder()
        _context.engine = ContextEngine(
            retriever=retriever,
            prompt_builder=prompt_builder,
        )

        # Check Ollama status
        if _context.engine.is_ready():
            logger.info("Ollama is running and models are available.")
        else:
            logger.warning(
                "Ollama is not available. Queries will fail until Ollama is started."
            )

        logger.info("ContextOS startup complete.")

    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        logger.warning("Some features may be unavailable.")

    yield  # Application runs here

    # Shutdown
    logger.info("ContextOS shutting down...")
    try:
        if _context.graph_store:
            _context.graph_store.close()
        if _context.vector_store:
            _context.vector_store.close()
        if _context.metadata_store:
            _context.metadata_store.close()
        logger.info("All connections closed.")
    except Exception as exc:
        logger.error("Shutdown error: %s", exc)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        A configured FastAPI app with all routers and middleware.
    """
    app = FastAPI(
        title="ContextOS",
        description=(
            "Privacy-first on-device AI context engine for knowledge workers. "
            "Query your emails, documents, meetings, and more — all locally."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware — localhost only for security
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from core.api.routers import graph, health, ingest, query

    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(graph.router)
    app.include_router(ingest.router)

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "ContextOS",
            "version": "0.1.0",
            "tagline": "Your private AI memory layer",
            "docs": "/docs",
        }

    return app


# Create the app instance for uvicorn
app = create_app()
