"""
app/services/llm_providers/base.py
------------------------------------
Provider interfaces for the LLM provider layer.

Legacy interface (model_router / model_router path):
    BaseLlmProvider — ABC used by MockProvider, OpenAIProvider, AzureOpenAIProvider

Part 6 interface (ProviderAdapterExecutor path):
    ProviderAdapter — Protocol used by MockProviderAdapter, OpenAIProviderAdapter,
                      AzureOpenAIProviderAdapter

Helper:
    sanitize_provider_metadata — strips unsafe keys from metadata dicts

Rules:
- Graph nodes must never import this module directly.
- All LLM calls go through app/services/model_router.py (legacy) or
  ProviderAdapterExecutor (Part 6).
- Provider-specific logic lives only in sibling modules.
- No env reads at import time.
- No SDK client created at import time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

from schemas.llm import LlmRequest, LlmResponse, LlmRoleConfig, LlmStreamChunk

# ---------------------------------------------------------------------------
# Unsafe metadata key set — used by sanitize_provider_metadata
# ---------------------------------------------------------------------------

_UNSAFE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "prompt",
        "system_prompt",
        "user_prompt",
        "messages",
        "query",
        "context",
        "api_key",
        "secret",
        "credential",
        "authorization",
        "raw_response",
    }
)


def sanitize_provider_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *metadata* with all unsafe keys removed.

    Unsafe keys include: prompt, system_prompt, user_prompt, messages, query,
    context, api_key, secret, credential, authorization, raw_response.

    Use this helper before placing any provider-sourced dict into
    ModelExecutionResult.metadata.
    """
    return {k: v for k, v in metadata.items() if k not in _UNSAFE_METADATA_KEYS}


# ---------------------------------------------------------------------------
# Legacy abstract base class — model_router / BaseLlmProvider path
# ---------------------------------------------------------------------------


class BaseLlmProvider(ABC):
    """Interface every LLM provider must satisfy (legacy model_router path)."""

    @abstractmethod
    def generate(self, request: LlmRequest, config: LlmRoleConfig) -> LlmResponse:
        """Return a complete LLM response for the given request.

        Args:
            request: The provider-neutral request.
            config:  Role-specific model configuration.

        Returns:
            A fully populated LlmResponse.

        Raises:
            LlmConfigurationError: If required config or env vars are missing.
            LlmGenerationError:    If the provider call fails.
        """

    @abstractmethod
    def stream(self, request: LlmRequest, config: LlmRoleConfig) -> Iterator[LlmStreamChunk]:
        """Stream LLM response chunks for the given request.

        Providers that do not support streaming must raise LlmProviderError with
        a clear message rather than silently returning an empty iterator.

        Args:
            request: The provider-neutral request.
            config:  Role-specific model configuration.

        Yields:
            LlmStreamChunk instances. The last chunk has is_final=True.

        Raises:
            LlmProviderError:      If streaming is not supported.
            LlmConfigurationError: If required config or env vars are missing.
            LlmGenerationError:    If the provider call fails during streaming.
        """


# ---------------------------------------------------------------------------
# Part 6 Protocol — ProviderAdapterExecutor path
# ---------------------------------------------------------------------------


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol for Part 6 provider adapters.

    Adapters receive explicitly resolved credentials and a fully resolved
    execution request.  They must not read os.environ, resolve secrets, or
    create SDK clients at import or construction time.

    Adapters must support injected fake clients for unit testing via a
    ``client_factory`` constructor parameter.

    Raises:
        LlmProviderConfigurationError: Missing/invalid credentials or config.
        LlmProviderExecutionError:     SDK/network call failed.
        LlmProviderResponseError:      Response missing or malformed.
    """

    def generate(
        self,
        *,
        request: ProviderExecutionRequest,  # noqa: F821 — forward ref resolved at runtime
        credentials: ProviderCredentials,  # noqa: F821 — forward ref resolved at runtime
    ) -> ModelExecutionResult:  # noqa: F821 — forward ref resolved at runtime
        ...
