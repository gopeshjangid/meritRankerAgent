"""
app/tests/test_records_schemas.py
-----------------------------------
Unit tests for app/schemas/records.py — QuestionRecord and PatternRecord.
No network calls, no AWS credentials required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.records import PatternRecord, QuestionRecord


class TestQuestionRecord:
    def test_minimal_valid_record(self):
        record = QuestionRecord(question_id="q-001")
        assert record.question_id == "q-001"
        assert record.text is None
        assert record.metadata == {}

    def test_full_valid_record(self):
        record = QuestionRecord(
            question_id="q-002",
            text="What is the derivative of x^2?",
            metadata={"topic": "calculus", "difficulty": 3},
        )
        assert record.text == "What is the derivative of x^2?"
        assert record.metadata["topic"] == "calculus"

    def test_missing_question_id_rejected(self):
        with pytest.raises(ValidationError):
            QuestionRecord()  # type: ignore[call-arg]

    def test_extra_fields_ignored(self):
        # model_config should allow extra fields for schema-agnostic use
        record = QuestionRecord(question_id="q-1", unknown_field="ignored")
        assert record.question_id == "q-1"


class TestPatternRecord:
    def test_minimal_valid_record(self):
        record = PatternRecord(pattern_id="p-001")
        assert record.pattern_id == "p-001"
        assert record.title is None
        assert record.metadata == {}

    def test_full_valid_record(self):
        record = PatternRecord(
            pattern_id="p-002",
            title="Quadratic formula",
            metadata={"subject": "algebra"},
        )
        assert record.title == "Quadratic formula"
        assert record.metadata["subject"] == "algebra"

    def test_missing_pattern_id_rejected(self):
        with pytest.raises(ValidationError):
            PatternRecord()  # type: ignore[call-arg]
