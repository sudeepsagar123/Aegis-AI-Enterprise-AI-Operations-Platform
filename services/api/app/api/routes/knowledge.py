"""
Aegis AI — Knowledge & RAG Routes.

Handles document ingestion, hybrid search, and knowledge graph queries.
"""

from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.api.schemas import (
    DocumentUploadResponse, SearchRequest, SearchResponse, SearchResult,
)
from app.core.logging import get_logger
from app.core.security import Permission, TokenPayload, require_permission
from app.db.repositories.domain import DocumentChunkRepository, DocumentRepository
from app.db.session import DbSession

logger = get_logger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.KNOWLEDGE_WRITE)),
):
    """
    Upload and ingest a document into the RAG knowledge base.

    Supported formats: PDF, DOCX, TXT, MD, CSV, XLSX
    The document will be chunked, embedded, and indexed for hybrid search.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    doc_repo = DocumentRepository(db)

    # Check for duplicate
    exists = await doc_repo.exists(
        org_id=uuid.UUID(user.org_id), content_hash=content_hash,
    )
    if exists:
        raise HTTPException(status_code=409, detail="Document already exists")

    doc = await doc_repo.create(
        org_id=uuid.UUID(user.org_id),
        title=file.filename,
        source_type="upload",
        content_hash=content_hash,
        mime_type=file.content_type,
        size_bytes=len(content),
        processing_status="queued",
    )

    # In production: publish to Kafka for async processing by the worker
    # await kafka_producer.send("document.ingest", {"document_id": str(doc.id)})

    logger.info("document_uploaded", doc_id=str(doc.id), filename=file.filename)

    return DocumentUploadResponse(
        id=doc.id, title=doc.title, source_type=doc.source_type,
        processing_status=doc.processing_status, chunk_count=0,
    )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge_base(
    request: SearchRequest,
    db: DbSession = None,  # type: ignore
    user: TokenPayload = Depends(require_permission(Permission.KNOWLEDGE_READ)),
):
    """
    Perform hybrid search (vector + keyword) across the knowledge base.

    Uses Reciprocal Rank Fusion to combine vector similarity (pgvector)
    and BM25 keyword search results for optimal retrieval.
    """
    chunk_repo = DocumentChunkRepository(db)

    # In production: generate embedding via OpenAI, run hybrid search
    # For now, return an empty result set
    logger.info("knowledge_search", query=request.query[:100], user_id=user.sub)

    return SearchResponse(
        results=[],
        query=request.query,
        total_results=0,
    )
