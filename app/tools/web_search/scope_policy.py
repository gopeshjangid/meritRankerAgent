"""Broad geographic scope and source-need detection for web search policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SourceScope = Literal["india", "world", "mixed", "unknown"]
SourceNeed = Literal[
    "practice_current_affairs",
    "official_exam_update",
    "economy",
    "government_schemes",
    "sports",
    "polity",
    "geography",
    "science",
    "environment",
    "general",
]

_CURRENT_AFFAIRS_REASONS: frozenset[str] = frozenset(
    {
        "current_affairs",
        "current_economy",
        "current_event",
        "explicit_latest_request",
        "freshness_required",
        "user_requested_web",
    }
)

_INDIA_SIGNALS: tuple[str, ...] = (
    " india ",
    " indian ",
    " bharat ",
    " domestic ",
    "india current affairs",
    "indian current affairs",
    "indian economy",
    "india economy",
    "indian polity",
    "indian government",
    "government of india",
    "for india",
)

_WORLD_SIGNALS: tuple[str, ...] = (
    " world ",
    " global ",
    " international ",
    " foreign ",
    " worldwide ",
    "global current affairs",
    "world current affairs",
    "international relations",
    "international current affairs",
    "world affairs",
)

_WORLD_ENTITIES: tuple[str, ...] = (
    "usa",
    " u.s.",
    " u.s ",
    "america",
    "iran",
    "china",
    "russia",
    "ukraine",
    "israel",
    "palestine",
    "europe",
    " eu ",
    "nato",
    " uk ",
    "britain",
    "france",
    "germany",
    "japan",
    "australia",
    "canada",
    "mexico",
    "brazil",
    "saudi",
    "pakistan",
    "bangladesh",
    "sri lanka",
    "nepal",
    "afghanistan",
    "taiwan",
    "korea",
)

_EXAM_LIFECYCLE_PHRASES: tuple[str, ...] = (
    "admit card",
    "hall ticket",
    "answer key",
    "scorecard",
    "official notification",
    "exam notification",
    "exam date",
    "exam result",
    "official result",
    "application form",
    "registration date",
    "application deadline",
    "cut off",
    "cutoff",
    "official syllabus",
    "eligibility criteria",
    "vacancy",
    "counselling",
    "counseling",
)

_EXAM_CONTEXT_TOKENS: tuple[str, ...] = (
    "upsc",
    "ssc",
    "sbi",
    "ibps",
    "nta",
    "neet",
    "jee",
    "cat",
    "ielts",
    "gre",
    "gate",
    "clat",
    "cuet",
    "po mains",
    "banking awareness",
)

_ECONOMY_SIGNALS: tuple[str, ...] = (
    "rbi",
    "repo rate",
    "inflation",
    "gdp",
    "budget",
    "monetary policy",
    "fiscal",
    "economy",
    "economic",
)

_SCHEME_SIGNALS: tuple[str, ...] = (
    "scheme",
    "yojana",
    "mission",
    "government scheme",
    "latest scheme",
    "benefit amount",
    "scheme benefit",
)

_SPORTS_SIGNALS: tuple[str, ...] = (
    "sports",
    "olympic",
    "cricket",
    "fifa",
    "world cup",
    "medal",
    "tournament",
)

_POLITY_SIGNALS: tuple[str, ...] = (
    "polity",
    "constitution",
    "lok sabha",
    "rajya sabha",
    "eci",
    "governance",
    "legal",
    "bill passed",
)

_GEOGRAPHY_SIGNALS: tuple[str, ...] = (
    "geography",
    "census",
    "climate zone",
    "isro launch",
    "imd",
    "weather pattern",
)

_SCIENCE_SIGNALS: tuple[str, ...] = (
    "isro",
    "drdo",
    "science",
    "space mission",
    "who guideline",
    "research",
)

_ENVIRONMENT_SIGNALS: tuple[str, ...] = (
    "environment",
    "climate",
    "pollution",
    "moef",
    "carbon",
    "cop ",
)


@dataclass(frozen=True)
class SourceScopePolicy:
    """Internal scope policy — not exposed in graph state or UI."""

    scope: SourceScope
    india_weight: int
    world_weight: int
    source_need: SourceNeed
    exam_context: str | None
    explicit_scope: bool
    official_exam_lifecycle: bool


def detect_source_scope_policy(
    *,
    query: str,
    web_search_query: str | None,
    web_search_reason: str | None,
) -> SourceScopePolicy:
    """Detect geographic scope, source need, and exam context from query signals."""
    combined = " ".join(
        part for part in (query, web_search_query or "") if part
    ).strip()
    lower = f" {combined.lower()} "

    official_lifecycle = has_exam_lifecycle_intent(
        combined,
        web_search_reason=web_search_reason,
    )
    exam_context = detect_exam_context(lower)
    source_need = _detect_source_need(
        lower,
        web_search_reason=web_search_reason,
        official_lifecycle=official_lifecycle,
    )
    scope, india_weight, world_weight, explicit_scope = _detect_scope(
        lower,
        source_need=source_need,
        web_search_reason=web_search_reason,
    )

    return SourceScopePolicy(
        scope=scope,
        india_weight=india_weight,
        world_weight=world_weight,
        source_need=source_need,
        exam_context=exam_context,
        explicit_scope=explicit_scope,
        official_exam_lifecycle=official_lifecycle,
    )


def has_exam_lifecycle_intent(
    text: str,
    *,
    web_search_reason: str | None = None,
) -> bool:
    """True when query asks for official exam/scheme lifecycle information."""
    if web_search_reason == "latest_exam_update":
        return True

    lower = text.lower()
    if any(phrase in lower for phrase in _EXAM_LIFECYCLE_PHRASES):
        return True

    if re.search(r"\bresult(s)?\b", lower) and any(
        token in lower for token in ("exam", "ielts", "gre", "upsc", "ssc", "score")
    ):
        return True

    if "notification" in lower and any(
        token in lower for token in ("exam", "official", "upsc", "ssc", "vacancy")
    ):
        return True

    if "eligibility" in lower and any(
        token in lower for token in ("exam", "scheme", "official", "apply")
    ):
        return True

    return False


def detect_exam_context(lower_padded: str) -> str | None:
    """Extract exam audience context — does not imply exam_updates routing."""
    for token in _EXAM_CONTEXT_TOKENS:
        if token in lower_padded:
            return token.upper()
    return None


def _detect_source_need(
    lower_padded: str,
    *,
    web_search_reason: str | None,
    official_lifecycle: bool,
) -> SourceNeed:
    if official_lifecycle:
        return "official_exam_update"
    if any(signal in lower_padded for signal in _ECONOMY_SIGNALS):
        return "economy"
    if any(signal in lower_padded for signal in _SCHEME_SIGNALS):
        return "government_schemes"
    if any(signal in lower_padded for signal in _SPORTS_SIGNALS):
        return "sports"
    if any(signal in lower_padded for signal in _POLITY_SIGNALS):
        return "polity"
    if any(signal in lower_padded for signal in _GEOGRAPHY_SIGNALS):
        return "geography"
    if any(signal in lower_padded for signal in _SCIENCE_SIGNALS):
        return "science"
    if any(signal in lower_padded for signal in _ENVIRONMENT_SIGNALS):
        return "environment"
    if web_search_reason in _CURRENT_AFFAIRS_REASONS or "current affairs" in lower_padded:
        return "practice_current_affairs"
    if web_search_reason == "current_economy":
        return "economy"
    return "general"


def _detect_scope(
    lower_padded: str,
    *,
    source_need: SourceNeed,
    web_search_reason: str | None,
) -> tuple[SourceScope, int, int, bool]:
    scrubbed = (
        lower_padded.replace("world cup", "  ")
        .replace("world war", "  ")
        .replace("world series", "  ")
    )
    india_hit = any(signal in lower_padded for signal in _INDIA_SIGNALS)
    world_hit = any(signal in scrubbed for signal in _WORLD_SIGNALS) or any(
        entity in lower_padded for entity in _WORLD_ENTITIES
    )

    if india_hit and world_hit:
        return "mixed", 50, 50, True
    if india_hit:
        return "india", 100, 0, True
    if world_hit:
        return "world", 0, 100, True

    if source_need in {"practice_current_affairs", "general"} or (
        web_search_reason in _CURRENT_AFFAIRS_REASONS
    ):
        return "mixed", 70, 30, False

    return "mixed", 70, 30, False
