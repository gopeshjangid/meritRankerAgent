"""Deterministic guards for official-only vs exam-prep-suitable queries."""

from __future__ import annotations

from tools.web_search.scope_policy import has_exam_lifecycle_intent

_EXAM_PREP_SUITABLE_PHRASES: tuple[str, ...] = (
    "monthly current affairs",
    "current affairs summary",
    "economy current affairs",
    "important current affairs",
    "explain latest",
    "summary of",
    "for ssc",
    "for upsc",
    "for sbi",
    "exam prep",
    "preparation",
)

_EXAM_PREP_SUITABLE_REASONS: frozenset[str] = frozenset(
    {
        "current_affairs",
        "current_economy",
        "current_event",
        "explicit_latest_request",
        "freshness_required",
        "user_requested_web",
    }
)


def is_official_only_query(
    query: str,
    *,
    web_search_query: str | None = None,
    web_search_reason: str | None = None,
) -> bool:
    """True when the query needs official confirmation (dates, results, eligibility)."""
    combined = " ".join(
        part for part in (query, web_search_query or "") if part
    )
    if has_exam_lifecycle_intent(combined, web_search_reason=web_search_reason):
        return True

    lower = combined.lower()
    if "scheme" in lower and any(
        token in lower
        for token in ("eligibility", "benefit", "application", "apply")
    ):
        return True

    return False


def is_exam_prep_suitable_query(
    query: str,
    *,
    web_search_query: str | None = None,
    web_search_reason: str | None = None,
) -> bool:
    """True when exam-prep sources may provide supporting summary context."""
    if is_official_only_query(
        query,
        web_search_query=web_search_query,
        web_search_reason=web_search_reason,
    ):
        return False

    combined = " ".join(
        part for part in (query, web_search_query or "") if part
    ).lower()

    if any(phrase in combined for phrase in _EXAM_PREP_SUITABLE_PHRASES):
        return True

    if web_search_reason in _EXAM_PREP_SUITABLE_REASONS:
        return True

    return False
