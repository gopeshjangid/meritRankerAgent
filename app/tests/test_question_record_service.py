"""
app/tests/test_question_record_service.py
-------------------------------------------
Unit tests for app/services/question_record_service.py.

All tests use mocks — no real AWS calls, no credentials required.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import config as cfg_module
from services.dynamodb_service import DynamoDbConfigurationError
from services.question_record_service import (
    fetch_pattern_record_by_id,
    fetch_pattern_records_by_ids,
    fetch_question_record_by_id,
    fetch_question_records_by_ids,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings():
    cfg_module._settings = None


def _fake_item(question_id: str = "q-1") -> dict:
    return {"question_id": question_id, "text": "What is algebra?", "difficulty": 2}


def _fake_pattern(pattern_id: str = "p-1") -> dict:
    return {"pattern_id": pattern_id, "title": "Linear equations"}


# ---------------------------------------------------------------------------
# Disabled flag
# ---------------------------------------------------------------------------


class TestDisabledFlag:
    def test_fetch_question_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "false")
        _reset_settings()

        with patch("services.question_record_service.get_item") as mock_get:
            result = fetch_question_record_by_id("q-1")

        mock_get.assert_not_called()
        assert result is None

    def test_fetch_pattern_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "false")
        _reset_settings()

        with patch("services.question_record_service.get_item") as mock_get:
            result = fetch_pattern_record_by_id("p-1")

        mock_get.assert_not_called()
        assert result is None

    def test_fetch_pattern_records_returns_empty_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "false")
        _reset_settings()

        with patch("services.question_record_service.batch_get_items") as mock_batch:
            result = fetch_pattern_records_by_ids(["p-1", "p-2"])

        mock_batch.assert_not_called()
        assert result == []

    def test_fetch_question_records_returns_empty_when_disabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "false")
        _reset_settings()

        with patch("services.question_record_service.batch_get_items") as mock_batch:
            result = fetch_question_records_by_ids(["q-1", "q-2"])

        mock_batch.assert_not_called()
        assert result == []

    def test_disabled_is_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_DYNAMODB_FETCH", raising=False)
        _reset_settings()

        result = fetch_question_record_by_id("q-1")
        assert result is None


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestConfigurationErrors:
    def test_missing_question_table_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_QUESTION_TABLE", "")
        _reset_settings()

        with pytest.raises(DynamoDbConfigurationError, match="DYNAMODB_QUESTION_TABLE"):
            fetch_question_record_by_id("q-1")

    def test_missing_pattern_table_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_PATTERN_TABLE", "")
        _reset_settings()

        with pytest.raises(DynamoDbConfigurationError, match="DYNAMODB_PATTERN_TABLE"):
            fetch_pattern_record_by_id("p-1")

    def test_missing_pattern_table_raises_on_batch_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_PATTERN_TABLE", "")
        _reset_settings()

        with pytest.raises(DynamoDbConfigurationError):
            fetch_pattern_records_by_ids(["p-1"])

    def test_missing_question_table_raises_on_batch_when_enabled(self, monkeypatch):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_QUESTION_TABLE", "")
        _reset_settings()

        with pytest.raises(DynamoDbConfigurationError):
            fetch_question_records_by_ids(["q-1"])


# ---------------------------------------------------------------------------
# fetch_question_record_by_id — enabled path
# ---------------------------------------------------------------------------


class TestFetchQuestionRecordById:
    def _setup(self, monkeypatch, table: str = "questions-table"):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_QUESTION_TABLE", table)
        _reset_settings()

    def test_uses_dynamodb_question_table(self, monkeypatch):
        self._setup(monkeypatch, table="my-questions")

        with patch(
            "services.question_record_service.get_item", return_value=_fake_item()
        ) as mock_get:
            fetch_question_record_by_id("q-1")

        mock_get.assert_called_once_with("my-questions", {"question_id": "q-1"})

    def test_returns_item_from_service(self, monkeypatch):
        self._setup(monkeypatch)
        fake = _fake_item("q-42")

        with patch("services.question_record_service.get_item", return_value=fake):
            result = fetch_question_record_by_id("q-42")

        assert result == fake

    def test_returns_none_when_not_found(self, monkeypatch):
        self._setup(monkeypatch)

        with patch("services.question_record_service.get_item", return_value=None):
            result = fetch_question_record_by_id("nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# fetch_pattern_record_by_id — enabled path
# ---------------------------------------------------------------------------


class TestFetchPatternRecordById:
    def _setup(self, monkeypatch, table: str = "patterns-table"):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_PATTERN_TABLE", table)
        _reset_settings()

    def test_uses_dynamodb_pattern_table(self, monkeypatch):
        self._setup(monkeypatch, table="my-patterns")

        with patch(
            "services.question_record_service.get_item", return_value=_fake_pattern()
        ) as mock_get:
            fetch_pattern_record_by_id("p-1")

        mock_get.assert_called_once_with("my-patterns", {"pattern_id": "p-1"})

    def test_returns_pattern_from_service(self, monkeypatch):
        self._setup(monkeypatch)
        fake = _fake_pattern("p-99")

        with patch("services.question_record_service.get_item", return_value=fake):
            result = fetch_pattern_record_by_id("p-99")

        assert result == fake

    def test_returns_none_when_not_found(self, monkeypatch):
        self._setup(monkeypatch)

        with patch("services.question_record_service.get_item", return_value=None):
            result = fetch_pattern_record_by_id("nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# fetch_pattern_records_by_ids — enabled path
# ---------------------------------------------------------------------------


class TestFetchPatternRecordsByIds:
    def _setup(self, monkeypatch, table: str = "patterns-table"):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_PATTERN_TABLE", table)
        _reset_settings()

    def test_empty_ids_returns_empty_without_aws_call(self, monkeypatch):
        self._setup(monkeypatch)

        with patch("services.question_record_service.batch_get_items") as mock_batch:
            result = fetch_pattern_records_by_ids([])

        mock_batch.assert_not_called()
        assert result == []

    def test_deduplicates_ids_before_batch(self, monkeypatch):
        self._setup(monkeypatch)

        with patch(
            "services.question_record_service.batch_get_items", return_value=[]
        ) as mock_batch:
            fetch_pattern_records_by_ids(["p-1", "p-2", "p-1", "p-3", "p-2"])

        sent_keys = mock_batch.call_args[0][1]
        sent_ids = [k["pattern_id"] for k in sent_keys]
        assert sent_ids == ["p-1", "p-2", "p-3"]

    def test_returns_records_from_batch(self, monkeypatch):
        self._setup(monkeypatch)
        fake_records = [_fake_pattern("p-1"), _fake_pattern("p-2")]

        with patch(
            "services.question_record_service.batch_get_items", return_value=fake_records
        ):
            result = fetch_pattern_records_by_ids(["p-1", "p-2"])

        assert len(result) == 2
        assert result[0]["pattern_id"] == "p-1"

    def test_uses_pattern_table(self, monkeypatch):
        self._setup(monkeypatch, table="special-patterns")

        with patch(
            "services.question_record_service.batch_get_items", return_value=[]
        ) as mock_batch:
            fetch_pattern_records_by_ids(["p-1"])

        mock_batch.assert_called_once()
        table_arg = mock_batch.call_args[0][0]
        assert table_arg == "special-patterns"

    def test_batch_ids_capped_at_max(self, monkeypatch):
        self._setup(monkeypatch)
        many_ids = [f"p-{i}" for i in range(50)]  # exceeds _MAX_BATCH_IDS=25

        with patch(
            "services.question_record_service.batch_get_items", return_value=[]
        ) as mock_batch:
            fetch_pattern_records_by_ids(many_ids)

        sent_keys = mock_batch.call_args[0][1]
        assert len(sent_keys) == 25


# ---------------------------------------------------------------------------
# fetch_question_records_by_ids — enabled path
# ---------------------------------------------------------------------------


class TestFetchQuestionRecordsByIds:
    def _setup(self, monkeypatch, table: str = "questions-table"):
        monkeypatch.setenv("ENABLE_DYNAMODB_FETCH", "true")
        monkeypatch.setenv("DYNAMODB_QUESTION_TABLE", table)
        _reset_settings()

    def test_empty_ids_returns_empty_without_aws_call(self, monkeypatch):
        self._setup(monkeypatch)

        with patch("services.question_record_service.batch_get_items") as mock_batch:
            result = fetch_question_records_by_ids([])

        mock_batch.assert_not_called()
        assert result == []

    def test_deduplicates_ids_before_batch(self, monkeypatch):
        self._setup(monkeypatch)

        with patch(
            "services.question_record_service.batch_get_items", return_value=[]
        ) as mock_batch:
            fetch_question_records_by_ids(["q-1", "q-1", "q-2"])

        sent_keys = mock_batch.call_args[0][1]
        sent_ids = [k["question_id"] for k in sent_keys]
        assert sent_ids == ["q-1", "q-2"]

    def test_returns_records_from_batch(self, monkeypatch):
        self._setup(monkeypatch)
        fake_records = [_fake_item("q-1"), _fake_item("q-2")]

        with patch(
            "services.question_record_service.batch_get_items", return_value=fake_records
        ):
            result = fetch_question_records_by_ids(["q-1", "q-2"])

        assert len(result) == 2

    def test_uses_question_table(self, monkeypatch):
        self._setup(monkeypatch, table="special-questions")

        with patch(
            "services.question_record_service.batch_get_items", return_value=[]
        ) as mock_batch:
            fetch_question_records_by_ids(["q-1"])

        table_arg = mock_batch.call_args[0][0]
        assert table_arg == "special-questions"
