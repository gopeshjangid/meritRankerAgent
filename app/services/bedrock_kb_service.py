"""
app/services/bedrock_kb_service.py
------------------------------------
Bedrock Knowledge Base retrieval service.

Public surface:
    retrieve_similar_context(query, max_results=None) -> RetrievalResponse

Architecture invariants:
    - ENABLE_KB_RETRIEVAL=false (default) → returns empty response; no client is created.
    - Graph nodes MUST NOT import boto3 or this module directly.
    - Retrieved content is UNTRUSTED; full content is NEVER logged.
    - Only ``retrieve`` is used; ``retrieve_and_generate`` is off-limits here.
      Generation stays in model_router.

[KB SERVICE FOUNDATION — not yet wired into the Doubt Solver graph]
"""

from __future__ import annotations

import logging
from typing import Any

from botocore.exceptions import ClientError

from config import get_settings
from schemas.retrieval import KnowledgeBaseResult, RetrievalResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class KnowledgeBaseServiceError(Exception):
    """Raised when the Bedrock KB retrieve call fails."""


class KnowledgeBaseConfigurationError(Exception):
    """Raised when KB is enabled but required configuration is missing."""


# ---------------------------------------------------------------------------
# Metadata helpers  (pure, no I/O)
# ---------------------------------------------------------------------------

# Keys from which to extract record identifiers from result metadata.
_RECORD_ID_KEYS = frozenset(
    {"record_id", "record_ids", "question_id", "pattern_id", "pattern_ids"}
)


def _extract_record_ids(metadata: dict[str, Any]) -> list[str]:
    """Best-effort extraction of record identifiers from KB result metadata.

    Handles string values, lists of strings, and mixed types.  Non-string
    entries are silently skipped; we do not raise on malformed metadata.
    """
    seen: list[str] = []
    for key in _RECORD_ID_KEYS:
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value:
            seen.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    seen.append(item)
    # Deduplicate while preserving order.
    deduped: list[str] = []
    visited: set[str] = set()
    for rid in seen:
        if rid not in visited:
            deduped.append(rid)
            visited.add(rid)
    return deduped[:20]  # cap at schema max_length


def _extract_source_id(location: dict[str, Any] | None) -> str | None:
    """Best-effort extraction of a human-readable source identifier.

    Inspects common location structures returned by Bedrock:
      - S3 object URI  (``s3Location.uri``)
      - Custom data source URI (``customDocumentLocation.id``)
      - Web crawler URL (``webLocation.url``)
    Returns None if no usable source can be found.
    """
    if not location:
        return None
    # Each location type is nested under its type key.
    for key in ("s3Location", "customDocumentLocation", "webLocation"):
        entry = location.get(key)
        if not isinstance(entry, dict):
            continue
        for field in ("uri", "id", "url"):
            candidate = entry.get(field)
            if isinstance(candidate, str) and candidate:
                return candidate[:512]
    return None


def _parse_result(raw: dict[str, Any]) -> KnowledgeBaseResult | None:
    """Convert one raw API result dict into a KnowledgeBaseResult.

    Returns None for results whose content is empty or cannot be parsed,
    so the caller can silently skip them.
    """
    content_block = raw.get("content") or {}
    text = content_block.get("text", "") if isinstance(content_block, dict) else ""
    if not isinstance(text, str) or not text.strip():
        return None
    # Enforce schema max_length to avoid downstream validation errors.
    if len(text) > 8000:
        text = text[:8000]

    score_raw = raw.get("score")
    score = float(score_raw) if isinstance(score_raw, (int, float)) else None

    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    location = raw.get("location") if isinstance(raw.get("location"), dict) else None
    source_id = _extract_source_id(location)

    record_ids = _extract_record_ids(metadata)

    return KnowledgeBaseResult(
        content=text,
        score=score,
        source_id=source_id,
        metadata=metadata,
        record_ids=record_ids,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve_similar_context(
    query: str,
    max_results: int | None = None,
) -> RetrievalResponse:
    """Query the Bedrock Knowledge Base and return structured results.

    Disabled path:
        When ``ENABLE_KB_RETRIEVAL=false`` (default) this function returns an
        empty ``RetrievalResponse`` with ``retrieval_source="disabled"`` and
        does NOT create a boto3 client or make any network call.

    Enabled path:
        Validates configuration, calls ``bedrock-agent-runtime:Retrieve``, and
        parses the results into ``KnowledgeBaseResult`` objects.

    Args:
        query:       The student query to retrieve context for.
        max_results: Number of results to request.  Falls back to
                     ``BEDROCK_KB_MAX_RESULTS`` setting when None.

    Returns:
        A ``RetrievalResponse`` with zero or more results.

    Raises:
        KnowledgeBaseConfigurationError: KB is enabled but ``BEDROCK_KB_ID`` is
                                         not set.
        KnowledgeBaseServiceError:       The Bedrock API call fails.
    """
    settings = get_settings()

    if not settings.enable_kb_retrieval:
        return RetrievalResponse(
            query=query,
            results=[],
            result_count=0,
            retrieval_source="disabled",
        )

    # --- Enabled path ---
    if not settings.bedrock_kb_id:
        raise KnowledgeBaseConfigurationError(
            "ENABLE_KB_RETRIEVAL=true but BEDROCK_KB_ID is not set. "
            "Set BEDROCK_KB_ID to your Bedrock Knowledge Base ID."
        )

    n = max_results if max_results is not None else settings.bedrock_kb_max_results

    # Deferred import keeps boto3 out of the hot path when KB is disabled.
    from services.aws_client_factory import get_bedrock_agent_runtime_client  # noqa: PLC0415

    client = get_bedrock_agent_runtime_client(
        region_name=settings.bedrock_kb_region or None
    )

    request: dict[str, Any] = {
        "knowledgeBaseId": settings.bedrock_kb_id,
        "retrievalQuery": {"text": query},
        "retrievalConfiguration": {
            "vectorSearchConfiguration": {"numberOfResults": n}
        },
    }

    try:
        response = client.retrieve(**request)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        raise KnowledgeBaseServiceError(
            f"Bedrock KB retrieve failed (code={error_code}). "
            "Check KB ID, region, and IAM permissions."
        ) from exc

    raw_results: list[dict[str, Any]] = response.get("retrievalResults") or []

    # Apply optional minimum score filter.
    parsed: list[KnowledgeBaseResult] = []
    for raw in raw_results:
        result = _parse_result(raw)
        if result is None:
            continue
        if settings.bedrock_kb_min_score is not None and result.score is not None:
            if result.score < settings.bedrock_kb_min_score:
                continue
        parsed.append(result)

    # Safe log — counts only; no query text, no content.
    logger.info(
        "KB retrieve complete",
        extra={"result_count": len(parsed), "max_results": n, "source": "bedrock_kb"},
    )

    return RetrievalResponse(
        query=query,
        results=parsed,
        result_count=len(parsed),
        retrieval_source="bedrock_kb",
    )
