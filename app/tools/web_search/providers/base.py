"""Provider interface for web search backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from tools.web_search.models import WebSearchProviderRequest, WebSearchProviderResult


class WebSearchProvider(ABC):
    """Provider adapter — maps neutral requests to vendor APIs."""

    @abstractmethod
    def search(self, request: WebSearchProviderRequest) -> WebSearchProviderResult:
        """Execute one provider search call."""
