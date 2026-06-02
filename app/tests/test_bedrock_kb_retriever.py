"""
tests/test_bedrock_kb_retriever.py
-----------------------------------
Unit tests for BedrockKnowledgeBaseRetriever — fake client only.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

import config as cfg_module
from services.context_retrieval.bedrock_kb_retriever import (
    BedrockKnowledgeBaseRetriever,
    build_metadata_filter,
    normalize_kb_metadata,
    parse_kb_retrieval_result,
)
from services.context_retrieval.context_models import ContextRetrievalRequest


def _reset_settings() -> None:
    cfg_module._settings = None


def _request() -> ContextRetrievalRequest:
    return ContextRetrievalRequest(
        request_id="req-kb-1",
        query="Explain successive discount pattern",
        subject="math",
        intent="explain",
        difficulty="advanced",
    )


def _raw_result(
    text: str = "Pattern rule",
    score: float = 0.88,
    metadata: dict | None = None,
) -> dict:
    meta = {
        "patternId": "pat-99",
        "subject": "QUANT",
        "patternTopicKey": "PROFIT_LOSS_DISCOUNT",
        "patternFamilyKey": "DISCOUNT",
        "complexityLevel": "3",
        "confidence": "1.00",
        "taxonomyReviewRequired": "false",
        "schemaVersion": "v2",
        "conceptTags": "discount,profit",
    }
    if metadata:
        meta.update(metadata)
    return {
        "content": {"text": text},
        "score": score,
        "metadata": meta,
        "location": {"s3Location": {"uri": "s3://bucket/pattern-sandbox/chunks/pat-99.txt"}},
    }


def _real_like_result(**overrides: object) -> dict:
    """Bedrock Retrieve shape observed in production-like KB chunks."""
    meta_overrides = overrides.pop("metadata", None) if "metadata" in overrides else None
    base: dict[str, Any] = {
        "content": {
            "text": "Pattern chunk text about successive discount for banking exams.",
        },
        "metadata": {
            "patternId": "abc123",
            "subject": "QUANT",
            "patternTopicKey": "PROFIT_LOSS_DISCOUNT",
            "patternFamilyKey": "SUCCESSIVE_DISCOUNT",
            "taxonomyReviewRequired": "false",
            "schemaVersion": "v2",
            "confidence": "1.00",
        },
        "score": 0.82,
    }
    if meta_overrides and isinstance(meta_overrides, dict):
        base["metadata"] = {**base["metadata"], **meta_overrides}
    base.update(overrides)
    return base


class TestParseKbRetrievalResult:
    def test_real_like_content_text_normalizes(self) -> None:
        item, skip = parse_kb_retrieval_result(_real_like_result(), lane="SUBJECT_ONLY")
        assert skip is None
        assert item is not None
        assert "successive discount" in item.text.lower()
        assert item.metadata["subject"] == "QUANT"
        assert item.source_id == "abc123"

    def test_string_content_normalizes(self) -> None:
        raw = {"content": "Plain string chunk text about profit.", "score": 0.7}
        item, skip = parse_kb_retrieval_result(raw, lane="BROAD_SEMANTIC")
        assert skip is None
        assert item is not None
        assert item.text.startswith("Plain string")

    def test_top_level_text_normalizes(self) -> None:
        raw = {"text": "Top-level text field chunk.", "score": 0.75}
        item, skip = parse_kb_retrieval_result(raw, lane="BROAD_SEMANTIC")
        assert skip is None
        assert item is not None

    def test_missing_metadata_kept_with_risk(self) -> None:
        raw = {"content": {"text": "Valid chunk without metadata."}, "score": 0.8}
        item, skip = parse_kb_retrieval_result(raw, lane="RELAXED_SUBJECT_ONLY")
        assert skip is None
        assert item is not None
        assert "missing_metadata" in (item.risk or "")

    def test_missing_pattern_id_kept_with_risk(self) -> None:
        raw = _real_like_result()
        raw["metadata"] = dict(raw["metadata"])
        raw["metadata"].pop("patternId", None)
        item, skip = parse_kb_retrieval_result(raw, lane="SUBJECT_ONLY")
        assert skip is None
        assert item is not None
        assert "missing_pattern_id" in (item.risk or "")

    def test_empty_text_skipped(self) -> None:
        item, skip = parse_kb_retrieval_result(
            {"content": {"text": "   "}, "score": 0.9},
            lane="SUBJECT_ONLY",
        )
        assert item is None
        assert skip == "empty_text"

    def test_invalid_shape_skipped(self) -> None:
        raw = {"content": 12345, "score": 0.9}
        item, skip = parse_kb_retrieval_result(raw, lane="SUBJECT_ONLY")
        assert item is None
        assert skip == "invalid_shape"

    def test_metadata_from_content_nested(self) -> None:
        raw = {
            "content": {
                "text": "Nested metadata chunk.",
                "metadata": {"subject": "quant", "patternTopicKey": "percentage"},
            },
            "score": 0.77,
        }
        item, skip = parse_kb_retrieval_result(raw, lane="SUBJECT_ONLY")
        assert skip is None
        assert item is not None
        assert item.metadata["subject"] == "QUANT"
        assert item.metadata["patternTopicKey"] == "PERCENTAGE"


class TestMetadataFilter:
    def test_builds_string_equals_filter(self) -> None:
        filt = build_metadata_filter(
            {
                "subject": "QUANT",
                "taxonomyReviewRequired": "false",
                "schemaVersion": "v2",
            }
        )
        assert filt is not None
        assert "equals" in str(filt) or "andAll" in str(filt)

    def test_no_difficulty_in_production_filter(self) -> None:
        filt = build_metadata_filter({"subject": "QUANT"})
        assert "advanced" not in str(filt)
        assert "complexityLevel" not in str(filt)


class TestMetadataNormalization:
    def test_confidence_string_preserved(self) -> None:
        meta = normalize_kb_metadata({"confidence": "1.00"})
        assert meta["confidence"] == "1.00"

    def test_pattern_topic_uppercased(self) -> None:
        meta = normalize_kb_metadata({"patternTopicKey": "profit_loss_discount"})
        assert meta["patternTopicKey"] == "PROFIT_LOSS_DISCOUNT"


class TestBedrockKnowledgeBaseRetriever:
    def test_fake_client_returns_normalized_items(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {"retrievalResults": [_raw_result()]}
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)

        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT", "taxonomyReviewRequired": "false"},
            retrieval_query="Question: discount\nSubject: QUANT",
            top_k=3,
        )
        assert aws_count == 1
        assert len(items) == 1
        assert items[0].source_type == "bedrock_kb"
        assert items[0].text == "Pattern rule"
        assert items[0].source_id == "pat-99"
        assert items[0].metadata["subject"] == "QUANT"
        assert items[0].metadata["confidence"] == "1.00"
        assert items[0].match_lane == "SUBJECT_ONLY"

    def test_metadata_filters_sent_to_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {"retrievalResults": []}
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={
                "subject": "QUANT",
                "taxonomyReviewRequired": "false",
                "schemaVersion": "v2",
            },
            retrieval_query="Question: test\nSubject: QUANT",
            top_k=3,
        )

        kwargs = client.retrieve.call_args.kwargs
        vector_cfg = kwargs["retrievalConfiguration"]["vectorSearchConfiguration"]
        assert "filter" in vector_cfg
        assert vector_cfg["numberOfResults"] == 3
        assert kwargs["retrievalQuery"]["text"].startswith("Question:")

    def test_missing_pattern_id_handled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        raw = _raw_result(metadata={"patternId": ""})
        raw["metadata"].pop("patternId", None)
        client = MagicMock()
        client.retrieve.return_value = {"retrievalResults": [raw]}
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, _ = retriever.retrieve_lane(
            request=_request(),
            lane="BROAD_SEMANTIC",
            filters={},
            retrieval_query="Question: test",
            top_k=3,
        )
        assert items[0].source_id == "s3://bucket/pattern-sandbox/chunks/pat-99.txt"
        assert items[0].risk == "missing_pattern_id"

    def test_three_valid_results_normalize(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        monkeypatch.delenv("BEDROCK_KB_MIN_SCORE", raising=False)
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {
            "retrievalResults": [
                _real_like_result(),
                _real_like_result(metadata={"patternId": "abc124"}),
                _real_like_result(metadata={"patternId": "abc125"}),
            ]
        }
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=3,
        )
        assert aws_count == 3
        assert len(items) == 3

    def test_skip_diagnostics_for_empty_content(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {
            "retrievalResults": [
                {"content": {"text": ""}, "score": 0.9, "metadata": {"subject": "QUANT"}},
                _real_like_result(),
            ]
        }
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        with caplog.at_level("DEBUG"):
            items, aws_count = retriever.retrieve_lane(
                request=_request(),
                lane="SUBJECT_ONLY",
                filters={"subject": "QUANT"},
                retrieval_query="Question: test",
                top_k=3,
            )
        assert aws_count == 2
        assert len(items) == 1
        lane_logs = [r.message for r in caplog.records if "context_retrieval_lane" in r.message]
        assert lane_logs
        assert "skipped_empty_text=1" in lane_logs[0]
        assert "Pattern chunk" not in lane_logs[0]
        detail_logs = [
            r.message for r in caplog.records if "context_retrieval_lane_detail" in r.message
        ]
        assert detail_logs
        assert "metadata_key_sets_sample" in detail_logs[0]

    def test_content_with_type_text_normalizes(self) -> None:
        raw = {
            "content": {"text": "Pattern with type field.", "type": "TEXT"},
            "score": 0.55,
            "metadata": {"subject": "QUANT", "patternId": "p-type"},
        }
        item, skip = parse_kb_retrieval_result(raw, lane="SUBJECT_ONLY")
        assert skip is None
        assert item is not None
        assert item.text == "Pattern with type field."

    def test_low_bedrock_score_still_normalizes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        monkeypatch.setenv("BEDROCK_KB_MIN_SCORE", "0.95")
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {
            "retrievalResults": [_real_like_result(score=0.12)],
        }
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=5,
        )
        assert aws_count == 1
        assert len(items) == 1
        assert items[0].score == 0.12

    def test_raw_aws_response_not_in_item(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        client = MagicMock()
        client.retrieve.return_value = {"retrievalResults": [_raw_result()]}
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, _ = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=3,
        )
        dumped = items[0].model_dump_json()
        assert "retrievalResults" not in dumped
        assert "s3Location" not in dumped

    def test_missing_kb_config_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "")
        _reset_settings()

        client = MagicMock()
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=3,
        )
        assert items == []
        assert aws_count == 0
        client.retrieve.assert_not_called()

    def test_aws_error_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "true")
        monkeypatch.setenv("BEDROCK_KB_ID", "kb-test-id")
        _reset_settings()

        client = MagicMock()
        client.retrieve.side_effect = ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "fail"}},
            operation_name="Retrieve",
        )
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=3,
        )
        assert items == []
        assert aws_count == 0

    def test_kb_disabled_returns_empty_without_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENABLE_KB_RETRIEVAL", "false")
        _reset_settings()

        client = MagicMock()
        retriever = BedrockKnowledgeBaseRetriever(client_factory=lambda _: client)
        items, aws_count = retriever.retrieve_lane(
            request=_request(),
            lane="SUBJECT_ONLY",
            filters={"subject": "QUANT"},
            retrieval_query="Question: test",
            top_k=3,
        )
        assert items == []
        assert aws_count == 0
        client.retrieve.assert_not_called()
