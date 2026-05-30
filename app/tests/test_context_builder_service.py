"""
app/tests/test_context_builder_service.py
-------------------------------------------
Unit tests for services/context_builder_service.py.

No external I/O, no AWS credentials, no LLM calls.
All tests use in-memory data.
"""

from __future__ import annotations

import config as cfg_module
from schemas.doubt_solver import QueryClassification
from schemas.retrieval import KnowledgeBaseResult
from services.context_builder_service import (
    _MAX_KB_SNIPPET_CHARS,
    _MAX_RECORD_TEXT_CHARS,
    ContextBundle,
    _safe_kb_snippet,
    _safe_record_summary,
    build_doubt_solver_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings():
    cfg_module._settings = None


def _classification(retrieval_need: str = "concept_context") -> QueryClassification:
    return QueryClassification(
        intent="explain_concept",  # type: ignore[arg-type]
        subject="math",
        confidence=0.75,
        retrieval_need=retrieval_need,  # type: ignore[arg-type]
    )


def _kb_result(
    content: str = "Algebra is a branch of mathematics.", score: float = 0.9
) -> KnowledgeBaseResult:
    return KnowledgeBaseResult(content=content, score=score, source_id="src-1")


def _dynamo_record(question_id: str = "q-1", text: str = "What is algebra?") -> dict:
    return {"question_id": question_id, "text": text}


# ---------------------------------------------------------------------------
# _safe_kb_snippet
# ---------------------------------------------------------------------------


class TestSafeKbSnippet:
    def test_short_content_unchanged(self):
        content = "Short text."
        assert _safe_kb_snippet(content) == content

    def test_long_content_truncated_to_limit(self):
        long = "x" * (_MAX_KB_SNIPPET_CHARS + 100)
        result = _safe_kb_snippet(long)
        assert len(result) == _MAX_KB_SNIPPET_CHARS

    def test_exact_limit_unchanged(self):
        exact = "y" * _MAX_KB_SNIPPET_CHARS
        assert _safe_kb_snippet(exact) == exact


# ---------------------------------------------------------------------------
# _safe_record_summary
# ---------------------------------------------------------------------------


class TestSafeRecordSummary:
    def test_returns_none_for_empty_record(self):
        assert _safe_record_summary({}) is None

    def test_returns_none_for_record_with_no_useful_fields(self):
        assert _safe_record_summary({"metadata": {"hidden": "stuff"}}) is None

    def test_includes_question_id(self):
        result = _safe_record_summary({"question_id": "q-42", "text": "Some text."})
        assert "q-42" in result

    def test_includes_pattern_id(self):
        result = _safe_record_summary({"pattern_id": "p-7", "title": "Patterns"})
        assert "p-7" in result

    def test_includes_text_content(self):
        result = _safe_record_summary({"question_id": "q-1", "text": "Test content"})
        assert "Test content" in result

    def test_truncates_long_text(self):
        long_text = "a" * (_MAX_RECORD_TEXT_CHARS + 50)
        result = _safe_record_summary({"question_id": "q-1", "text": long_text})
        assert long_text not in result
        assert len(result) < len(long_text) + 20  # accounting for "ID: q-1 | Content: "

    def test_does_not_include_metadata(self):
        result = _safe_record_summary({
            "question_id": "q-1",
            "text": "Safe text.",
            "metadata": {"secret": "leaked"},
        })
        assert "leaked" not in result
        assert "secret" not in result

    def test_identifier_only_record(self):
        result = _safe_record_summary({"question_id": "q-99"})
        assert "q-99" in result


# ---------------------------------------------------------------------------
# build_doubt_solver_context — empty inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_returns_context_bundle_instance(self):
        result = build_doubt_solver_context(
            query="test",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[],
        )
        assert isinstance(result, ContextBundle)

    def test_empty_inputs_return_empty_context(self):
        result = build_doubt_solver_context(
            query="test",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[],
        )
        assert result.context == ""
        assert result.source_count == 0
        assert result.is_truncated is False

    def test_empty_inputs_not_truncated(self):
        result = build_doubt_solver_context(
            query="test",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[],
            max_chars=100,
        )
        assert result.is_truncated is False


# ---------------------------------------------------------------------------
# build_doubt_solver_context — KB results
# ---------------------------------------------------------------------------


class TestKbResultsIncluded:
    def test_safety_header_present_when_kb_results(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result()],
            dynamodb_records=[],
        )
        assert "reference material" in result.context.lower()
        assert "not instructions" in result.context.lower()

    def test_kb_content_snippet_included(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("Algebra helps solve equations.")],
            dynamodb_records=[],
        )
        assert "Algebra helps solve equations." in result.context

    def test_source_count_equals_kb_results_count(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result(), _kb_result("Second snippet.")],
            dynamodb_records=[],
        )
        assert result.source_count == 2

    def test_large_kb_content_snippet_truncated_per_item(self):
        long_content = "Z" * (_MAX_KB_SNIPPET_CHARS + 200)
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[KnowledgeBaseResult(content=long_content)],
            dynamodb_records=[],
        )
        # Only the snippet (truncated) should appear, not the full content.
        assert long_content not in result.context

    def test_reference_label_in_context(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result()],
            dynamodb_records=[],
        )
        assert "[Reference 1]" in result.context


# ---------------------------------------------------------------------------
# build_doubt_solver_context — DynamoDB records
# ---------------------------------------------------------------------------


class TestDynamoDbRecordsIncluded:
    def test_record_summary_included(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[_dynamo_record("q-5", "What is ratio?")],
        )
        assert "q-5" in result.context
        assert "What is ratio?" in result.context

    def test_empty_record_skipped(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[{}],
        )
        # No useful record → source_count should be 0 even though a record was passed.
        assert result.source_count == 0

    def test_metadata_not_blindly_dumped(self):
        record = {
            "question_id": "q-1",
            "text": "Safe text.",
            "metadata": {"internal_key": "sensitive_value", "nested": {"deep": "data"}},
        }
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[record],
        )
        assert "sensitive_value" not in result.context
        assert "internal_key" not in result.context

    def test_source_count_counts_records_with_content(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[],
            dynamodb_records=[
                _dynamo_record("q-1", "Text 1"),
                {},  # empty — skipped
                _dynamo_record("q-2", "Text 2"),
            ],
        )
        assert result.source_count == 2


# ---------------------------------------------------------------------------
# build_doubt_solver_context — mixed KB + DynamoDB
# ---------------------------------------------------------------------------


class TestMixedSources:
    def test_both_sources_included(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("KB snippet.")],
            dynamodb_records=[_dynamo_record("q-3", "DynamoDB text.")],
        )
        assert "KB snippet." in result.context
        assert "DynamoDB text." in result.context

    def test_total_source_count_is_sum(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result(), _kb_result("Second.")],
            dynamodb_records=[_dynamo_record()],
        )
        assert result.source_count == 3


# ---------------------------------------------------------------------------
# build_doubt_solver_context — truncation
# ---------------------------------------------------------------------------


class TestContextTruncation:
    def test_context_not_truncated_within_limit(self):
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("Short.")],
            dynamodb_records=[],
            max_chars=6000,
        )
        assert result.is_truncated is False

    def test_context_truncated_when_exceeds_max_chars(self):
        # Use a very small max_chars to force truncation.
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("A" * 300)],
            dynamodb_records=[],
            max_chars=50,
        )
        assert result.is_truncated is True
        assert len(result.context) == 50

    def test_custom_max_chars_respected(self, monkeypatch):
        monkeypatch.setenv("DOUBT_SOLVER_MAX_CONTEXT_CHARS", "100")
        _reset_settings()
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("B" * 300)],
            dynamodb_records=[],
        )
        assert len(result.context) <= 100

    def test_default_max_chars_from_settings(self, monkeypatch):
        monkeypatch.setenv("DOUBT_SOLVER_MAX_CONTEXT_CHARS", "6000")
        _reset_settings()
        result = build_doubt_solver_context(
            query="q",
            classification=_classification(),
            kb_results=[_kb_result("Normal sized content.")],
            dynamodb_records=[],
        )
        assert len(result.context) <= 6000
