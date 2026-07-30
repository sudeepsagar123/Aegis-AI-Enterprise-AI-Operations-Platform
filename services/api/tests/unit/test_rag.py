"""
Aegis AI — Unit Tests for RAG Pipeline.
"""

from __future__ import annotations

import pytest

from app.services.rag_pipeline import ChunkResult, DocumentChunker, HybridSearcher


class TestDocumentChunker:
    @pytest.fixture
    def chunker(self):
        return DocumentChunker(chunk_size=200, chunk_overlap=50, min_chunk_size=20)

    def test_short_text_single_chunk(self, chunker):
        text = "This is a short text that fits in one chunk."
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_long_text_multiple_chunks(self, chunker):
        text = "First paragraph with enough content. " * 20 + "\n\n" + "Second paragraph. " * 20
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_chunk_indices_sequential(self, chunker):
        text = "Paragraph one. " * 30 + "\n\n" + "Paragraph two. " * 30
        chunks = chunker.chunk_text(text)
        indices = [c["index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_clean_text_normalizes_whitespace(self):
        text = "Multiple   spaces   here\r\nWindows  line  endings"
        cleaned = DocumentChunker._clean_text(text)
        assert "\r\n" not in cleaned
        assert "  " not in cleaned

    def test_empty_text(self, chunker):
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0]["content"] == "")


class TestHybridSearcher:
    @pytest.fixture
    def searcher(self):
        return HybridSearcher(k=60)

    def _make_result(self, chunk_id: str, score: float = 0.9) -> ChunkResult:
        return ChunkResult(
            chunk_id=chunk_id,
            document_id="doc-1",
            document_title="Test Doc",
            content="test content",
            score=score,
            source_type="upload",
            metadata={},
        )

    def test_rrf_combines_results(self, searcher):
        vector_results = [self._make_result("a"), self._make_result("b")]
        keyword_results = [self._make_result("b"), self._make_result("c")]

        combined = searcher.reciprocal_rank_fusion(vector_results, keyword_results)

        ids = [r.chunk_id for r in combined]
        # "b" appears in both, should rank highest
        assert ids[0] == "b"
        assert len(combined) == 3  # a, b, c

    def test_rrf_respects_weights(self, searcher):
        vector_results = [self._make_result("v1")]
        keyword_results = [self._make_result("k1")]

        combined = searcher.reciprocal_rank_fusion(
            vector_results, keyword_results,
            vector_weight=0.9, keyword_weight=0.1,
        )

        # Vector result should score higher with 0.9 weight
        assert combined[0].chunk_id == "v1"

    def test_rrf_empty_inputs(self, searcher):
        combined = searcher.reciprocal_rank_fusion([], [])
        assert combined == []

    def test_rrf_single_source(self, searcher):
        vector_results = [self._make_result("a"), self._make_result("b")]
        combined = searcher.reciprocal_rank_fusion(vector_results, [])
        assert len(combined) == 2
