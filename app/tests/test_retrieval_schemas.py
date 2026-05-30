"""
app/tests/test_retrieval_schemas.py
-------------------------------------
Unit tests for app/schemas/retrieval.py — KnowledgeBaseResult and RetrievalResponse.
No network calls, no AWS credentials required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.retrieval import KnowledgeBaseResult, RetrievalResponse


class TestKnowledgeBaseResultValid:
    def test_minimal_valid_result(self):
        result = KnowledgeBaseResult(content="some content")
        assert result.content == "some content"
        assert result.score is None
        assert result.source_id is None
        assert result.metadata == {}
        assert result.record_ids == []

    def test_full_valid_result(self):
        result = KnowledgeBaseResult(
            content="A" * 100,
            score=0.95,
            source_id="s3://bucket/key",
            metadata={"topic": "algebra"},
            record_ids=["r1", "r2"],
        )
        assert result.score == 0.95
        assert result.source_id == "s3://bucket/key"
        assert result.metadata == {"topic": "algebra"}
        assert result.record_ids == ["r1", "r2"]

    def test_score_zero_is_valid(self):
        result = KnowledgeBaseResult(content="text", score=0.0)
        assert result.score == 0.0

    def test_score_one_is_valid(self):
        result = KnowledgeBaseResult(content="text", score=1.0)
        assert result.score == 1.0

    def test_source_id_max_length_512(self):
        result = KnowledgeBaseResult(content="text", source_id="x" * 512)
        assert len(result.source_id) == 512

    def test_record_ids_up_to_20(self):
        result = KnowledgeBaseResult(
            content="text", record_ids=[str(i) for i in range(20)]
        )
        assert len(result.record_ids) == 20


class TestKnowledgeBaseResultRejections:
    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseResult(content="")

    def test_content_over_8000_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseResult(content="x" * 8001)

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseResult(content="text", score=-0.1)

    def test_source_id_over_512_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseResult(content="text", source_id="x" * 513)

    def test_record_ids_over_20_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseResult(
                content="text", record_ids=[str(i) for i in range(21)]
            )


class TestRetrievalResponseValid:
    def test_empty_disabled_response(self):
        resp = RetrievalResponse(
            query="what is algebra",
            results=[],
            result_count=0,
            retrieval_source="disabled",
        )
        assert resp.result_count == 0
        assert resp.retrieval_source == "disabled"
        assert resp.results == []

    def test_bedrock_kb_source(self):
        result = KnowledgeBaseResult(content="definition of algebra")
        resp = RetrievalResponse(
            query="what is algebra",
            results=[result],
            result_count=1,
            retrieval_source="bedrock_kb",
        )
        assert resp.retrieval_source == "bedrock_kb"
        assert len(resp.results) == 1

    def test_fallback_source(self):
        resp = RetrievalResponse(
            query="q",
            results=[],
            result_count=0,
            retrieval_source="fallback",
        )
        assert resp.retrieval_source == "fallback"

    def test_default_retrieval_source_is_disabled(self):
        resp = RetrievalResponse(query="q", results=[], result_count=0)
        assert resp.retrieval_source == "disabled"

    def test_result_count_zero(self):
        resp = RetrievalResponse(query="q", results=[], result_count=0)
        assert resp.result_count == 0


class TestRetrievalResponseRejections:
    def test_invalid_retrieval_source_rejected(self):
        with pytest.raises(ValidationError):
            RetrievalResponse(
                query="q",
                results=[],
                result_count=0,
                retrieval_source="unknown_source",  # type: ignore[arg-type]
            )
