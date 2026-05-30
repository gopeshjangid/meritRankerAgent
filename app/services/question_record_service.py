"""
app/services/question_record_service.py
-----------------------------------------
Domain-specific service for fetching question and pattern records from DynamoDB.

Public surface:
    fetch_question_record_by_id(question_id) -> dict | None
    fetch_pattern_record_by_id(pattern_id) -> dict | None
    fetch_pattern_records_by_ids(pattern_ids) -> list[dict]
    fetch_question_records_by_ids(question_ids) -> list[dict]

Architecture invariants:
    - ENABLE_DYNAMODB_FETCH=false (default) → returns None/[] without any AWS call.
    - Table names come from settings (DYNAMODB_QUESTION_TABLE / DYNAMODB_PATTERN_TABLE).
    - Missing table name when enabled → raises DynamoDbConfigurationError immediately.
    - Full record payloads are NEVER logged.
    - Graph nodes MUST NOT import this module directly.
    - This service does NOT assume a finalised DynamoDB schema — records are returned
      as plain dicts.  [NOT VERIFIED] real table schema.

Assumed key names:
    - question_id  →  primary key for the questions table
    - pattern_id   →  primary key for the patterns table
    These are defaults and can be made config-driven in a future part.

[DOMAIN SERVICE FOUNDATION — not yet wired into the Doubt Solver graph]
"""

from __future__ import annotations

import logging
from typing import Any

from config import get_settings
from services.dynamodb_service import (
    DynamoDbConfigurationError,
    batch_get_items,
    get_item,
)

logger = logging.getLogger(__name__)

# Hard cap on batch IDs accepted by this domain service.
_MAX_BATCH_IDS = 25

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deduplicate_ids(ids: list[str]) -> list[str]:
    """Deduplicate *ids* while preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for id_ in ids:
        if id_ not in seen:
            result.append(id_)
            seen.add(id_)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_question_record_by_id(question_id: str) -> dict[str, Any] | None:
    """Fetch a single question record by its primary key.

    Args:
        question_id: The unique question identifier.

    Returns:
        Plain Python dict of the question record, or None if not found or disabled.

    Raises:
        DynamoDbConfigurationError: DynamoDB is enabled but DYNAMODB_QUESTION_TABLE
                                    is not configured.
        DynamoDbServiceError:       The DynamoDB call fails.
    """
    settings = get_settings()
    if not settings.enable_dynamodb_fetch:
        return None

    if not settings.dynamodb_question_table:
        raise DynamoDbConfigurationError(
            "ENABLE_DYNAMODB_FETCH=true but DYNAMODB_QUESTION_TABLE is not set. "
            "Set DYNAMODB_QUESTION_TABLE to your DynamoDB table name."
        )

    logger.info(
        "Fetching question record",
        extra={"table": settings.dynamodb_question_table},
    )
    return get_item(
        settings.dynamodb_question_table,
        {"question_id": question_id},
    )


def fetch_pattern_record_by_id(pattern_id: str) -> dict[str, Any] | None:
    """Fetch a single pattern record by its primary key.

    Args:
        pattern_id: The unique pattern identifier.

    Returns:
        Plain Python dict of the pattern record, or None if not found or disabled.

    Raises:
        DynamoDbConfigurationError: DynamoDB is enabled but DYNAMODB_PATTERN_TABLE
                                    is not configured.
        DynamoDbServiceError:       The DynamoDB call fails.
    """
    settings = get_settings()
    if not settings.enable_dynamodb_fetch:
        return None

    if not settings.dynamodb_pattern_table:
        raise DynamoDbConfigurationError(
            "ENABLE_DYNAMODB_FETCH=true but DYNAMODB_PATTERN_TABLE is not set. "
            "Set DYNAMODB_PATTERN_TABLE to your DynamoDB table name."
        )

    logger.info(
        "Fetching pattern record",
        extra={"table": settings.dynamodb_pattern_table},
    )
    return get_item(
        settings.dynamodb_pattern_table,
        {"pattern_id": pattern_id},
    )


def fetch_pattern_records_by_ids(pattern_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch multiple pattern records by their primary keys in a single batch call.

    Args:
        pattern_ids: List of pattern identifiers.  Deduplicated and capped at
                     _MAX_BATCH_IDS before the DynamoDB call.

    Returns:
        List of plain Python dicts.  Missing records are absent (not an error).
        Returns [] when disabled or when *pattern_ids* is empty.

    Raises:
        DynamoDbConfigurationError: DynamoDB is enabled but DYNAMODB_PATTERN_TABLE
                                    is not configured.
        DynamoDbServiceError:       The DynamoDB call fails.
    """
    settings = get_settings()
    if not settings.enable_dynamodb_fetch:
        return []

    if not pattern_ids:
        return []

    deduped = _deduplicate_ids(pattern_ids)[:_MAX_BATCH_IDS]

    if not settings.dynamodb_pattern_table:
        raise DynamoDbConfigurationError(
            "ENABLE_DYNAMODB_FETCH=true but DYNAMODB_PATTERN_TABLE is not set. "
            "Set DYNAMODB_PATTERN_TABLE to your DynamoDB table name."
        )

    logger.info(
        "Fetching pattern records batch",
        extra={"table": settings.dynamodb_pattern_table, "count": len(deduped)},
    )
    keys = [{"pattern_id": pid} for pid in deduped]
    return batch_get_items(settings.dynamodb_pattern_table, keys)


def fetch_question_records_by_ids(question_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch multiple question records by their primary keys in a single batch call.

    Args:
        question_ids: List of question identifiers.  Deduplicated and capped at
                      _MAX_BATCH_IDS before the DynamoDB call.

    Returns:
        List of plain Python dicts.  Missing records are absent (not an error).
        Returns [] when disabled or when *question_ids* is empty.

    Raises:
        DynamoDbConfigurationError: DynamoDB is enabled but DYNAMODB_QUESTION_TABLE
                                    is not configured.
        DynamoDbServiceError:       The DynamoDB call fails.
    """
    settings = get_settings()
    if not settings.enable_dynamodb_fetch:
        return []

    if not question_ids:
        return []

    deduped = _deduplicate_ids(question_ids)[:_MAX_BATCH_IDS]

    if not settings.dynamodb_question_table:
        raise DynamoDbConfigurationError(
            "ENABLE_DYNAMODB_FETCH=true but DYNAMODB_QUESTION_TABLE is not set. "
            "Set DYNAMODB_QUESTION_TABLE to your DynamoDB table name."
        )

    logger.info(
        "Fetching question records batch",
        extra={"table": settings.dynamodb_question_table, "count": len(deduped)},
    )
    keys = [{"question_id": qid} for qid in deduped]
    return batch_get_items(settings.dynamodb_question_table, keys)
