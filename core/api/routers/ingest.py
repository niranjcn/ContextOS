"""
ContextOS Ingest Router.

Provides endpoints for ingesting text and files into the ContextOS
knowledge base.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.api.models import IngestResponse, IngestStatusResponse, IngestTextRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

# Supported file types for upload
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


@router.post(
    "/text",
    response_model=IngestResponse,
    summary="Ingest raw text",
    description="Ingest raw text content with metadata into the knowledge base.",
)
async def ingest_text(request: IngestTextRequest) -> IngestResponse:
    """
    Ingest raw text content directly into the pipeline.

    Processes the text through entity extraction, chunking, and storage.
    """
    from core.api.main import get_pipeline

    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Ingestion pipeline not initialized.")

    try:
        result = pipeline.process_text(
            text=request.text,
            doc_id=request.doc_id,
            source=request.source,
            metadata=request.metadata,
        )
        return IngestResponse(
            doc_id=result["doc_id"],
            chunks_created=result["chunks_created"],
            entities=result.get("entities", {}),
            status=result["status"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Text ingestion failed: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Ingestion failed: {str(exc)}"
        )


@router.post(
    "/file",
    response_model=IngestResponse,
    summary="Ingest a file",
    description="Upload and ingest a file (PDF, TXT, DOCX, MD) into the knowledge base.",
)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    """
    Ingest an uploaded file into the pipeline.

    Supports PDF, TXT, DOCX, and MD file formats.
    """
    from core.api.main import get_pipeline

    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Ingestion pipeline not initialized.")

    # Validate file type
    filename = file.filename or "upload"
    extension = ""
    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[-1].lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{extension}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    try:
        # Read file content
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="replace")

        # Generate document ID from content hash
        content_hash = hashlib.sha256(content_bytes).hexdigest()[:16]
        doc_id = f"upload_{content_hash}"

        result = pipeline.process_text(
            text=content,
            doc_id=doc_id,
            source="file_upload",
            metadata={
                "filename": filename,
                "content_type": file.content_type or "application/octet-stream",
                "size_bytes": len(content_bytes),
            },
        )

        return IngestResponse(
            doc_id=result["doc_id"],
            chunks_created=result["chunks_created"],
            entities=result.get("entities", {}),
            status=result["status"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("File ingestion failed: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"File ingestion failed: {str(exc)}"
        )


@router.get(
    "/status",
    response_model=IngestStatusResponse,
    summary="Ingestion status",
    description="Returns statistics about processed documents by source.",
)
async def ingest_status() -> IngestStatusResponse:
    """Get ingestion statistics from the metadata store."""
    from core.api.main import get_metadata_store

    metadata_store = get_metadata_store()
    if metadata_store is None:
        raise HTTPException(status_code=503, detail="Metadata store not initialized.")

    try:
        stats = metadata_store.get_stats()
        return IngestStatusResponse(
            total=stats["total"],
            by_source=stats["by_source"],
        )
    except Exception as exc:
        logger.error("Failed to get ingest status: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve status: {str(exc)}"
        )
