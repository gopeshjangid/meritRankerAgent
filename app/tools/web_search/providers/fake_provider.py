"""Deterministic fake provider for unit tests."""

from __future__ import annotations

from tools.web_search.models import (
    SearchAttemptKind,
    WebSearchItem,
    WebSearchProviderRequest,
    WebSearchProviderResult,
)
from tools.web_search.providers.base import WebSearchProvider


class FakeWebSearchProvider(WebSearchProvider):
    """Returns canned items; optionally filters by include_domains."""

    def __init__(self, items: list[WebSearchItem] | None = None) -> None:
        self._items = items or [
            WebSearchItem(
                title="Latest RBI repo rate update",
                url="https://rbi.org.in/policy-update",
                snippet="The RBI maintained the repo rate in the latest monetary policy review.",
                source="rbi.org.in",
                published_at="2026-05-15",
                score=0.9,
            ),
            WebSearchItem(
                title="Latest government current affairs update",
                url="https://pib.gov.in/current-affairs",
                snippet="Press Information Bureau release on recent government policy updates.",
                source="pib.gov.in",
                published_at="2026-05-15",
                score=0.88,
            ),
        ]

    def search(self, request: WebSearchProviderRequest) -> WebSearchProviderResult:
        attempt = str(request.metadata.get("attempt") or "authoritative")
        valid_attempts = {
            "authoritative",
            "authoritative_plus_reputed",
            "exam_prep_fallback",
            "generic_fallback",
        }
        attempt_kind: SearchAttemptKind = (
            attempt if attempt in valid_attempts else "authoritative"  # type: ignore[assignment]
        )
        filtered = self._items
        if request.include_domains:
            allowed = {d.lower().removeprefix("www.") for d in request.include_domains}
            filtered = [
                item
                for item in self._items
                if _matches_domain(item, allowed)
            ]
        if request.exclude_domains:
            blocked = {d.lower().removeprefix("www.") for d in request.exclude_domains}
            filtered = [
                item for item in filtered if not _matches_domain(item, blocked)
            ]
        return WebSearchProviderResult(
            items=filtered[: request.max_results],
            provider="fake",
            attempt=attempt_kind,
        )


def _matches_domain(item: WebSearchItem, domains: set[str]) -> bool:
    source = (item.source or "").lower().removeprefix("www.")
    if source in domains:
        return True
    return any(source.endswith(domain) or domain in source for domain in domains)
