"""Web search trigger rules for context retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from config import Settings, get_settings
from services.context_retrieval.context_models import ContextRetrievalRequest
from tools.web_search.web_search_tool import credentials_ready

_DIRECT_WEB_REASONS: frozenset[str] = frozenset(
    {
        "explicit_latest_request",
        "current_affairs",
        "current_economy",
        "latest_exam_update",
        "current_event",
        "user_requested_web",
    }
)

_FALLBACK_WEB_SUBJECTS: frozenset[str] = frozenset({"general"})

_BLOCKED_FALLBACK_SUBJECTS: frozenset[str] = frozenset({"math", "reasoning", "english"})

_FALLBACK_DIFFICULTIES: frozenset[str] = frozenset({"intermediate", "advanced"})

_FRESHNESS_KEYWORDS: tuple[str, ...] = (
    "latest",
    "current",
    "recent",
    "today",
    "this month",
    "this year",
    "recently",
    "now",
    "this week",
    "updated",
    "new policy",
    "new scheme",
)

_FRESHNESS_REASONS: frozenset[str] = frozenset({"freshness_required"})


@dataclass(frozen=True)
class WebSearchDecision:
    """Resolved web search policy for one retrieval request."""

    need_web_search: bool
    reason: str
    query: str
    direct_web: bool
    fallback_web: bool
    will_call: bool
    enabled: bool
    provider: str


def resolve_web_search_query(request: ContextRetrievalRequest) -> str:
    """Return the query string to send to the web provider."""
    if request.web_search_query and request.web_search_query.strip():
        return request.web_search_query.strip()
    return request.query.strip()


def has_freshness_signal(query: str) -> bool:
    """True when the student query signals time-sensitive information."""
    lower = query.lower()
    return any(keyword in lower for keyword in _FRESHNESS_KEYWORDS)


def evaluate_web_search_decision(
    request: ContextRetrievalRequest,
    settings: Settings,
) -> WebSearchDecision:
    """Decide whether and how web search should run for this request."""
    enabled = settings.web_search_enabled
    provider = settings.web_search_provider
    reason = (request.web_search_reason or "none").strip() or "none"
    search_query = resolve_web_search_query(request)
    credentials_ready = _credentials_ready(settings, provider)
    can_call = enabled and credentials_ready

    direct_web = bool(request.need_web_search)
    fallback_web = False
    if not direct_web:
        fallback_web = should_attempt_web_fallback(
            request,
            kb_selected=False,
            settings=settings,
        )

    will_call = can_call and (direct_web or fallback_web)
    return WebSearchDecision(
        need_web_search=bool(request.need_web_search),
        reason=reason,
        query=search_query,
        direct_web=direct_web,
        fallback_web=fallback_web,
        will_call=will_call,
        enabled=enabled,
        provider=provider,
    )


def should_skip_kb_for_direct_web(request: ContextRetrievalRequest) -> bool:
    """Skip KB when classifier requests direct fresh web context."""
    if not request.need_web_search:
        return False
    reason = (request.web_search_reason or "").strip()
    if reason in _DIRECT_WEB_REASONS:
        return True
    return has_freshness_signal(request.query)


def should_attempt_web_fallback(
    request: ContextRetrievalRequest,
    *,
    kb_selected: bool,
    settings: Settings | None = None,
) -> bool:
    """KB miss fallback — only for freshness-friendly general queries."""
    if request.need_web_search or kb_selected:
        return False

    settings = settings or get_settings()
    if not settings.web_search_enabled:
        return False

    if request.subject in _BLOCKED_FALLBACK_SUBJECTS:
        return False

    if request.subject not in _FALLBACK_WEB_SUBJECTS:
        return False

    if request.difficulty not in _FALLBACK_DIFFICULTIES:
        return False

    reason = (request.web_search_reason or "").strip()
    if reason in _FRESHNESS_REASONS:
        return True

    return has_freshness_signal(request.query)


def _credentials_ready(settings: Settings, provider: str) -> bool:
    _ = provider
    return credentials_ready(settings)
