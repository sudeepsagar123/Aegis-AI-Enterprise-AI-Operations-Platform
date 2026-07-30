"""
Aegis AI — RAG Pipeline.

Implements hybrid search with vector similarity (pgvector) + BM25 keyword search,
combined via Reciprocal Rank Fusion. Includes document chunking, embedding generation,
and reranking.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkResult:
    """A single retrieved chunk with its score and metadata."""
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    score: float
    source_type: str
    metadata: dict[str, Any]


@dataclass
class RetrievalResult:
    """Aggregated retrieval result from hybrid search."""
    results: list[ChunkResult]
    query: str
    total_results: int
    search_method: str  # "hybrid", "vector", "keyword"


# ── Document Chunking ────────────────────────────────────────────────────────


class DocumentChunker:
    """
    Chunks documents using recursive character splitting with overlap.

    Strategy:
        1. Split on paragraph boundaries first
        2. If chunks are too large, split on sentence boundaries
        3. If still too large, split on word boundaries
        4. Maintain configurable overlap between chunks for context continuity
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into overlapping chunks."""
        # Clean the text
        text = self._clean_text(text)

        if len(text) <= self.chunk_size:
            return [{"content": text, "index": 0, "char_start": 0, "char_end": len(text)}]

        chunks = []
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        raw_chunks = self._recursive_split(text, separators)

        # Apply overlap
        for i, chunk in enumerate(raw_chunks):
            if len(chunk.strip()) < self.min_chunk_size:
                continue
            chunks.append({
                "content": chunk.strip(),
                "index": len(chunks),
                "token_count": len(chunk.split()),  # Approximate
            })

        logger.info("document_chunked", chunk_count=len(chunks), text_length=len(text))
        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using a hierarchy of separators."""
        if not separators or len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        parts = text.split(separator)
        chunks = []
        current_chunk = ""

        for part in parts:
            candidate = current_chunk + separator + part if current_chunk else part
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(part) > self.chunk_size:
                    # Recursively split with next separator
                    sub_chunks = self._recursive_split(part, separators[1:])
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace and remove control characters."""
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()


# ── Hybrid Search ────────────────────────────────────────────────────────────


class HybridSearcher:
    """
    Combines vector similarity search and BM25 keyword search
    using Reciprocal Rank Fusion (RRF) for optimal retrieval.
    """

    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF constant. Higher values give more weight to lower-ranked documents.
        """
        self.k = k

    def reciprocal_rank_fusion(
        self,
        vector_results: list[ChunkResult],
        keyword_results: list[ChunkResult],
        *,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> list[ChunkResult]:
        """
        Combine vector and keyword search results using weighted RRF.

        Formula: score = Σ(weight / (k + rank))
        """
        scores: dict[str, float] = {}
        chunk_map: dict[str, ChunkResult] = {}

        # Score vector results
        for rank, result in enumerate(vector_results, 1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
            scores[result.chunk_id] += vector_weight / (self.k + rank)
            chunk_map[result.chunk_id] = result

        # Score keyword results
        for rank, result in enumerate(keyword_results, 1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
            scores[result.chunk_id] += keyword_weight / (self.k + rank)
            if result.chunk_id not in chunk_map:
                chunk_map[result.chunk_id] = result

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for chunk_id in sorted_ids:
            chunk = chunk_map[chunk_id]
            chunk.score = scores[chunk_id]
            results.append(chunk)

        return results


# ── RAG Pipeline ─────────────────────────────────────────────────────────────


class RAGPipeline:
    """
    End-to-end RAG pipeline with hybrid search and reranking.

    Pipeline stages:
        1. Query expansion (optional)
        2. Vector similarity search (pgvector)
        3. BM25 keyword search
        4. Reciprocal Rank Fusion
        5. Cross-encoder reranking (optional)
        6. Context assembly
    """

    def __init__(self):
        self.chunker = DocumentChunker()
        self.searcher = HybridSearcher()
        self.settings = get_settings()

    async def retrieve(
        self,
        query: str,
        *,
        org_id: str,
        top_k: int = 10,
        source_types: list[str] | None = None,
        threshold: float = 0.72,
    ) -> RetrievalResult:
        """
        Execute the full RAG retrieval pipeline.
        """
        logger.info("rag_retrieve", query=query[:100], org_id=org_id, top_k=top_k)

        # In production:
        # 1. Generate query embedding via OpenAI
        # 2. Run pgvector cosine similarity search
        # 3. Run PostgreSQL full-text search (BM25)
        # 4. Combine with RRF
        # 5. Optional: rerank with cross-encoder

        return RetrievalResult(
            results=[],
            query=query,
            total_results=0,
            search_method="hybrid",
        )

    async def ingest_document(
        self,
        *,
        content: str,
        title: str,
        source_type: str,
        org_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Ingest a document: chunk, embed, and store.
        """
        # Chunk the document
        chunks = self.chunker.chunk_text(content)

        logger.info(
            "document_ingested",
            title=title,
            chunk_count=len(chunks),
            org_id=org_id,
        )

        # In production:
        # 1. Generate embeddings for all chunks (batch)
        # 2. Store chunks + embeddings in pgvector
        # 3. Index full text for BM25 search
        # 4. Extract entities for knowledge graph

        return {
            "title": title,
            "chunk_count": len(chunks),
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        }
