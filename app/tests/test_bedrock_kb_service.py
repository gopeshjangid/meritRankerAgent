"""
app/tests/test_bedrock_kb_service.py
--------------------------------------
Unit tests for app/services/bedrock_kb_service.py.

All tests use mocks — no real AWS calls, no credentials required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

import config as cfg_module
from schemas.retrieval import RetrievalResponse
from services.bedrock_kb_service import (
    KnowledgeBaseConfigurationError,
    KnowledgeBaseServiceError,
    _extract_record_ids,
    _extract_source_id,
    _parse_result,
    retrieve_similar_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_settings():
    """Force get_settings() to re-read os.environ on next call."""
    cfg_module._settings = None


def _make_client_error(code: str = "InternalServerError") -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "test error"}},
        operation_name="Retrieve",
    )


def _raw_result(
    text: str = "algebra is cool",
    score: float = 0.9,
    metadata: dict | None = None,
    location: dict | None = None,
) -> dict:
    return {
        "content": {"text": text},
        "score": score,
        "metadata": metadata or {},
        "location": location,
    }


# ---------------------------------------------------------------------------
# Disabled flag
# ---------------------------------------------------------------------------


class TestDisabledFlag:
    def test_disabled_returns_empty_response_without_creating_client(
        self, monkeypatch
    ):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "false")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client"
        ) as mock_factory:
            resp = retrieve_similar_context("what is algebra?")

        mock_factory.assert_not_called()
        assert isinstance(resp, RetrievalResponse)
        assert resp.retrieval_source == "disabled"
        assert resp.results == []
        assert resp.result_count == 0

    def test_disabled_is_default(self, monkeypatch):
        monkeypatch.delenv("ENABLE_KB_RETRIEVAL", raising=False)
        _reset_settings()

        resp = retrieve_similar_context("test query")
        assert resp.retrieval_source == "disabled"


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestConfigurationErrors:
    def test_enabled_without_kb_id_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "")
        _reset_settings()

        with pytest.raises(KnowledgeBaseConfigurationError, match="BEDROCK_KB_ID"):
            retrieve_similar_context("test query")

    def test_enabled_without_kb_id_missing_env_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
        _reset_settings()

        with pytest.raises(KnowledgeBaseConfigurationError):
            retrieve_similar_context("test query")


# ---------------------------------------------------------------------------
# Enabled path — successful retrieval
# ---------------------------------------------------------------------------


class TestEnabledPath:
    def _setup(self, monkeypatch, kb_id: str = "kb-123"):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", kb_id)
        monkeypatch.setenv("BEDROCK_KB_MAX_RESULTS", "5")
        monkeypatch.delenv("BEDROCK_KB_MIN_SCORE", raising=False)
        _reset_settings()

    def test_parses_content_score_metadata(self, monkeypatch):
        self._setup(monkeypatch)
        fake_response = {
            "retrievalResults": [
                _raw_result(text="Algebra is a branch of mathematics.", score=0.87)
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = fake_response

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("what is algebra?")

        assert resp.retrieval_source == "bedrock_kb"
        assert resp.result_count == 1
        assert len(resp.results) == 1
        result = resp.results[0]
        assert result.content == "Algebra is a branch of mathematics."
        assert result.score == pytest.approx(0.87)

    def test_passes_correct_request_to_client(self, monkeypatch):
        self._setup(monkeypatch)
        mock_client = MagicMock()
        mock_client.retrieve.return_value = {"retrievalResults": []}

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            retrieve_similar_context("test query")

        call_kwargs = mock_client.retrieve.call_args[1]
        assert call_kwargs["knowledgeBaseId"] == "kb-123"
        assert call_kwargs["retrievalQuery"]["text"] == "test query"
        assert (
            call_kwargs["retrievalConfiguration"]["vectorSearchConfiguration"][
                "numberOfResults"
            ]
            == 5
        )

    def test_max_results_explicit_override(self, monkeypatch):
        self._setup(monkeypatch)
        mock_client = MagicMock()
        mock_client.retrieve.return_value = {"retrievalResults": []}

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            retrieve_similar_context("query", max_results=3)

        call_kwargs = mock_client.retrieve.call_args[1]
        assert (
            call_kwargs["retrievalConfiguration"]["vectorSearchConfiguration"][
                "numberOfResults"
            ]
            == 3
        )

    def test_max_results_from_settings_default(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        monkeypatch.setenv("BEDROCK_KB_MAX_RESULTS", "7")
        _reset_settings()

        mock_client = MagicMock()
        mock_client.retrieve.return_value = {"retrievalResults": []}

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            retrieve_similar_context("query")

        call_kwargs = mock_client.retrieve.call_args[1]
        assert (
            call_kwargs["retrievalConfiguration"]["vectorSearchConfiguration"][
                "numberOfResults"
            ]
            == 7
        )

    def test_empty_results_returns_empty_response(self, monkeypatch):
        self._setup(monkeypatch)
        mock_client = MagicMock()
        mock_client.retrieve.return_value = {"retrievalResults": []}

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("rare query")

        assert resp.result_count == 0
        assert resp.results == []
        assert resp.retrieval_source == "bedrock_kb"

    def test_result_count_matches_list_length(self, monkeypatch):
        self._setup(monkeypatch)
        fake_response = {
            "retrievalResults": [
                _raw_result(text="First result", score=0.9),
                _raw_result(text="Second result", score=0.8),
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = fake_response

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("query")

        assert resp.result_count == 2
        assert len(resp.results) == 2


# ---------------------------------------------------------------------------
# Minimum score filter
# ---------------------------------------------------------------------------


class TestMinScoreFilter:
    def test_results_below_min_score_are_filtered(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        monkeypatch.setenv("BEDROCK_KB_MIN_SCORE", "0.8")
        _reset_settings()

        fake_response = {
            "retrievalResults": [
                _raw_result(text="High quality", score=0.95),
                _raw_result(text="Low quality", score=0.6),
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = fake_response

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("query")

        assert resp.result_count == 1
        assert resp.results[0].content == "High quality"

    def test_no_min_score_returns_all_results(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        monkeypatch.delenv("BEDROCK_KB_MIN_SCORE", raising=False)
        _reset_settings()

        fake_response = {
            "retrievalResults": [
                _raw_result(text="High quality", score=0.95),
                _raw_result(text="Low quality", score=0.1),
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = fake_response

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("query")

        assert resp.result_count == 2


# ---------------------------------------------------------------------------
# ClientError → KnowledgeBaseServiceError
# ---------------------------------------------------------------------------


class TestClientError:
    def test_client_error_raises_service_error(self, monkeypatch):
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        _reset_settings()

        mock_client = MagicMock()
        mock_client.retrieve.side_effect = _make_client_error("AccessDeniedException")

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            with pytest.raises(KnowledgeBaseServiceError, match="AccessDeniedException"):
                retrieve_similar_context("query")

    def test_service_error_message_is_safe(self, monkeypatch):
        """The error message must not echo the query or raw API response."""
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        _reset_settings()

        mock_client = MagicMock()
        mock_client.retrieve.side_effect = _make_client_error("ThrottlingException")

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            with pytest.raises(KnowledgeBaseServiceError) as exc_info:
                retrieve_similar_context("secret student query")

        assert "secret student query" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# record_id / record_ids extraction
# ---------------------------------------------------------------------------


class TestRecordIdExtraction:
    def test_record_id_string_extracted(self):
        meta = {"record_id": "r-001"}
        assert "r-001" in _extract_record_ids(meta)

    def test_record_ids_list_extracted(self):
        meta = {"record_ids": ["r-001", "r-002"]}
        ids = _extract_record_ids(meta)
        assert ids == ["r-001", "r-002"]

    def test_question_id_extracted(self):
        meta = {"question_id": "q-99"}
        assert "q-99" in _extract_record_ids(meta)

    def test_pattern_id_extracted(self):
        meta = {"pattern_id": "p-7"}
        assert "p-7" in _extract_record_ids(meta)

    def test_pattern_ids_list_extracted(self):
        meta = {"pattern_ids": ["p-1", "p-2"]}
        ids = _extract_record_ids(meta)
        assert "p-1" in ids
        assert "p-2" in ids

    def test_empty_metadata_returns_empty_list(self):
        assert _extract_record_ids({}) == []

    def test_duplicates_deduplicated(self):
        meta = {"record_id": "r-001", "record_ids": ["r-001", "r-002"]}
        ids = _extract_record_ids(meta)
        assert ids.count("r-001") == 1

    def test_non_string_values_skipped_safely(self):
        meta = {"record_id": 12345, "record_ids": [None, 42, "r-valid"]}
        ids = _extract_record_ids(meta)
        assert ids == ["r-valid"]

    def test_integration_metadata_record_ids_in_result(self, monkeypatch):
        """Full pipeline: metadata record IDs are present in parsed result."""
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-123")
        _reset_settings()

        fake_response = {
            "retrievalResults": [
                _raw_result(
                    text="concept explanation",
                    metadata={"record_id": "rec-42", "topic": "algebra"},
                )
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = fake_response

        with patch(
            "services.aws_client_factory.get_bedrock_agent_runtime_client",
            return_value=mock_client,
        ):
            resp = retrieve_similar_context("algebra question")

        assert "rec-42" in resp.results[0].record_ids


# ---------------------------------------------------------------------------
# Malformed metadata
# ---------------------------------------------------------------------------


class TestMalformedMetadata:
    def test_none_metadata_handled_safely(self):
        raw = {"content": {"text": "valid text"}, "score": 0.9, "metadata": None}
        result = _parse_result(raw)
        assert result is not None
        assert result.metadata == {}

    def test_non_dict_metadata_handled_safely(self):
        raw = {
            "content": {"text": "valid text"},
            "score": 0.8,
            "metadata": "invalid_string",
        }
        result = _parse_result(raw)
        assert result is not None
        assert result.metadata == {}

    def test_missing_content_text_returns_none(self):
        raw = {"content": {"byteContent": "base64data"}, "score": 0.5}
        result = _parse_result(raw)
        assert result is None

    def test_empty_content_text_returns_none(self):
        raw = {"content": {"text": "   "}, "score": 0.5}
        result = _parse_result(raw)
        assert result is None

    def test_missing_content_block_returns_none(self):
        raw = {"score": 0.5}
        result = _parse_result(raw)
        assert result is None


# ---------------------------------------------------------------------------
# Source ID extraction
# ---------------------------------------------------------------------------


class TestSourceIdExtraction:
    def test_s3_uri_extracted(self):
        location = {"s3Location": {"uri": "s3://bucket/prefix/file.txt"}}
        assert _extract_source_id(location) == "s3://bucket/prefix/file.txt"

    def test_custom_document_id_extracted(self):
        location = {"customDocumentLocation": {"id": "doc-001"}}
        assert _extract_source_id(location) == "doc-001"

    def test_web_location_url_extracted(self):
        location = {"webLocation": {"url": "https://example.com/page"}}
        assert _extract_source_id(location) == "https://example.com/page"

    def test_none_location_returns_none(self):
        assert _extract_source_id(None) is None

    def test_empty_location_returns_none(self):
        assert _extract_source_id({}) is None

    def test_uri_truncated_to_512(self):
        location = {"s3Location": {"uri": "s3://" + "x" * 510}}
        result = _extract_source_id(location)
        assert result is not None
        assert len(result) == 512
