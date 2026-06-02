"""
app/services/context_retrieval/bedrock_kb_retriever.py
-------------------------------------------------------
Bedrock Knowledge Base Retrieve API adapter.

Uses Retrieve only — no RetrieveAndGenerate, no generation.
Raw AWS responses are normalised to RetrievedContextItem and never leak upward.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

from config import get_settings
from services.context_retrieval.context_models import (
    ContextRetrievalRequest,
    RetrievedContextItem,
)

logger = logging.getLogger(__name__)

ClientFactory = Callable[[str | None], Any]

_SAFE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "patternId",
        "subject",
        "patternTopicKey",
        "patternFamilyKey",
        "complexityLevel",
        "confidence",
        "taxonomyReviewRequired",
        "schemaVersion",
        "conceptTags",
    }
)


@dataclass
class LaneSkipDiagnostics:
    """Safe per-lane skip counters — no chunk text or raw AWS payloads."""

    skipped_empty_text: int = 0
    skipped_missing_content: int = 0
    skipped_invalid_shape: int = 0
    skipped_decode_error: int = 0
    skipped_other: int = 0
    content_key_sets_sample: list[list[str]] = field(default_factory=list)
    metadata_key_sets_sample: list[list[str]] = field(default_factory=list)

    def record_skip(self, reason: str) -> None:
        mapping = {
            "empty_text": "skipped_empty_text",
            "missing_content": "skipped_missing_content",
            "invalid_shape": "skipped_invalid_shape",
            "decode_error": "skipped_decode_error",
        }
        attr = mapping.get(reason, "skipped_other")
        current = getattr(self, attr)
        setattr(self, attr, current + 1)


def build_metadata_filter(filters: dict[str, str]) -> dict[str, Any] | None:
    """Build a Bedrock KB metadata filter from string key/value pairs."""
    equals_clauses: list[dict[str, Any]] = []
    for key, value in filters.items():
        if value is None or value == "":
            continue
        equals_clauses.append({"equals": {"key": key, "value": str(value)}})

    if not equals_clauses:
        return None
    if len(equals_clauses) == 1:
        return equals_clauses[0]
    return {"andAll": equals_clauses}


def _extract_safe_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: raw[key] for key in _SAFE_METADATA_KEYS if key in raw}


def normalize_kb_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize KB metadata string values for safe downstream comparison."""
    extracted = _extract_safe_metadata(raw)
    normalized: dict[str, Any] = {}
    for key, value in extracted.items():
        if value is None or value == "":
            continue
        if key == "subject":
            normalized[key] = str(value).strip().upper()
        elif key in {"patternTopicKey", "patternFamilyKey"}:
            normalized[key] = str(value).strip().upper()
        elif key == "taxonomyReviewRequired":
            normalized[key] = str(value).strip().lower()
        elif key == "schemaVersion":
            normalized[key] = str(value).strip().lower()
        elif key == "conceptTags":
            tags = [t.strip().upper() for t in str(value).split(",") if t.strip()]
            normalized[key] = ",".join(tags)
        else:
            normalized[key] = value
    return normalized


def _extract_raw_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata")
    if isinstance(metadata, dict) and metadata:
        return metadata
    content = raw.get("content")
    if isinstance(content, dict):
        nested = content.get("metadata")
        if isinstance(nested, dict) and nested:
            return nested
    return {}


def _content_key_sample(content: Any) -> list[str]:
    if isinstance(content, dict):
        return sorted(str(key) for key in content.keys())
    if isinstance(content, str):
        return ["<str>"]
    if content is None:
        return []
    return ["<other>"]


def _extract_result_text(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract chunk text from a Bedrock retrieval result. Returns (text, skip_reason)."""
    top_level_text = raw.get("text")
    if isinstance(top_level_text, str) and top_level_text.strip():
        return top_level_text.strip(), None

    content = raw.get("content")
    if content is None:
        return None, "missing_content"

    if isinstance(content, str):
        stripped = content.strip()
        if stripped:
            return stripped, None
        return None, "empty_text"

    if not isinstance(content, dict):
        return None, "invalid_shape"

    text = content.get("text")
    if isinstance(text, str):
        stripped = text.strip()
        if stripped:
            return stripped, None
        return None, "empty_text"

    byte_content = content.get("byteContent")
    if byte_content is not None:
        try:
            if isinstance(byte_content, (bytes, bytearray)):
                decoded = bytes(byte_content).decode("utf-8")
            elif isinstance(byte_content, str):
                decoded = base64.b64decode(byte_content).decode("utf-8")
            else:
                return None, "invalid_shape"
            if decoded.strip():
                return decoded.strip(), None
            return None, "empty_text"
        except (UnicodeDecodeError, ValueError):
            return None, "decode_error"

    if content:
        return None, "missing_content"
    return None, "invalid_shape"


def parse_kb_retrieval_result(
    raw: dict[str, Any],
    *,
    lane: str,
) -> tuple[RetrievedContextItem | None, str | None]:
    """Parse one Bedrock KB result into RetrievedContextItem or return skip reason."""
    text, skip_reason = _extract_result_text(raw)
    if skip_reason or not text:
        return None, skip_reason or "empty_text"

    if len(text) > 8000:
        text = text[:8000]

    score_raw = raw.get("score")
    score = float(score_raw) if isinstance(score_raw, (int, float)) else None

    metadata = _extract_raw_metadata(raw)
    safe_metadata = normalize_kb_metadata(metadata)

    risks: list[str] = []
    if not safe_metadata:
        risks.append("missing_metadata")

    pattern_id = safe_metadata.get("patternId")
    source_id: str | None = None
    if pattern_id is not None and str(pattern_id).strip():
        source_id = str(pattern_id)[:512]
    else:
        risks.append("missing_pattern_id")
        location = raw.get("location") if isinstance(raw.get("location"), dict) else None
        if location:
            for loc_key in ("s3Location", "customDocumentLocation", "webLocation"):
                entry = location.get(loc_key)
                if isinstance(entry, dict):
                    for field_name in ("uri", "id", "url"):
                        candidate = entry.get(field_name)
                        if isinstance(candidate, str) and candidate:
                            source_id = candidate[:512]
                            break
                if source_id:
                    break

    title = safe_metadata.get("title") or metadata.get("title") or metadata.get("pattern_name")
    title_str = str(title)[:256] if title else None
    risk = ", ".join(dict.fromkeys(risks)) if risks else None

    return (
        RetrievedContextItem(
            source_type="bedrock_kb",
            text=text,
            score=score,
            source_id=source_id,
            metadata=safe_metadata,
            title=title_str,
            match_lane=lane,
            risk=risk,
        ),
        None,
    )


class BedrockKnowledgeBaseRetriever:
    """Retrieve candidate chunks from AWS Bedrock Knowledge Base."""

    def __init__(
        self,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._client_factory = client_factory

    def retrieve_lane(
        self,
        *,
        request: ContextRetrievalRequest,
        lane: str,
        filters: dict[str, str],
        retrieval_query: str,
        top_k: int,
        relaxed_filters: bool = False,
    ) -> tuple[list[RetrievedContextItem], int]:
        """Return normalised KB items and raw AWS result count for one lane."""
        settings = get_settings()

        if not settings.enable_kb_retrieval:
            return [], 0

        if not settings.bedrock_kb_id:
            logger.warning(
                "context_retrieval  request_id=%s  kb_config_missing=true",
                request.request_id,
            )
            return [], 0

        if self._client_factory is None:
            from services.aws_client_factory import (  # noqa: PLC0415
                get_bedrock_agent_runtime_client,
            )

            client_factory = get_bedrock_agent_runtime_client
        else:
            client_factory = self._client_factory

        client = client_factory(settings.bedrock_kb_region or None)

        vector_config: dict[str, Any] = {"numberOfResults": top_k}
        metadata_filter = build_metadata_filter(filters)
        if metadata_filter is not None:
            vector_config["filter"] = metadata_filter

        api_request: dict[str, Any] = {
            "knowledgeBaseId": settings.bedrock_kb_id,
            "retrievalQuery": {"text": retrieval_query},
            "retrievalConfiguration": {"vectorSearchConfiguration": vector_config},
        }

        try:
            response = client.retrieve(**api_request)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            logger.warning(
                "context_retrieval  request_id=%s  kb_retrieve_error  lane=%s  "
                "error_type=%s",
                request.request_id,
                lane,
                error_code,
            )
            return [], 0

        raw_results: list[dict[str, Any]] = (
            response.get("retrievalResults") or response.get("results") or []
        )
        aws_count = len(raw_results)
        diagnostics = LaneSkipDiagnostics()
        for raw in raw_results[:3]:
            diagnostics.content_key_sets_sample.append(_content_key_sample(raw.get("content")))
            diagnostics.metadata_key_sets_sample.append(
                sorted(_extract_raw_metadata(raw).keys())
            )

        items: list[RetrievedContextItem] = []
        bedrock_scores: list[float] = []
        bedrock_score_missing_count = 0
        for raw in raw_results:
            item, skip_reason = parse_kb_retrieval_result(raw, lane=lane)
            if skip_reason:
                diagnostics.record_skip(skip_reason)
                continue
            if item is None:
                diagnostics.record_skip("skipped_other")
                continue
            if item.score is not None:
                bedrock_scores.append(item.score)
            else:
                bedrock_score_missing_count += 1
            items.append(item)

        score_min = min(bedrock_scores) if bedrock_scores else None
        score_max = max(bedrock_scores) if bedrock_scores else None
        score_avg = sum(bedrock_scores) / len(bedrock_scores) if bedrock_scores else None

        logger.info(
            "context_retrieval_lane  request_id=%s  lane=%s  filter_keys=%s  "
            "top_k=%d  aws_result_count=%d  normalized_count=%d  relaxed_filters=%s  "
            "skipped_empty_text=%d  skipped_missing_content=%d  skipped_invalid_shape=%d  "
            "skipped_decode_error=%d  skipped_other=%d  "
            "bedrock_score_min=%s  bedrock_score_max=%s  bedrock_score_avg=%s  "
            "bedrock_score_missing_count=%d",
            request.request_id,
            lane,
            sorted(filters.keys()),
            top_k,
            aws_count,
            len(items),
            relaxed_filters,
            diagnostics.skipped_empty_text,
            diagnostics.skipped_missing_content,
            diagnostics.skipped_invalid_shape,
            diagnostics.skipped_decode_error,
            diagnostics.skipped_other,
            f"{score_min:.4f}" if score_min is not None else "none",
            f"{score_max:.4f}" if score_max is not None else "none",
            f"{score_avg:.4f}" if score_avg is not None else "none",
            bedrock_score_missing_count,
        )
        logger.debug(
            "context_retrieval_lane_detail  request_id=%s  lane=%s  "
            "metadata_key_sets_sample=%s  content_key_sets_sample=%s",
            request.request_id,
            lane,
            diagnostics.metadata_key_sets_sample,
            diagnostics.content_key_sets_sample,
        )
        return items, aws_count
