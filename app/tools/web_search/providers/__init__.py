"""Web search provider adapters."""

from tools.web_search.providers.base import WebSearchProvider
from tools.web_search.providers.fake_provider import FakeWebSearchProvider
from tools.web_search.providers.tavily_provider import TavilyWebSearchProvider

__all__ = [
    "FakeWebSearchProvider",
    "TavilyWebSearchProvider",
    "WebSearchProvider",
]
