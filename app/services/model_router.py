"""
app/services/model_router.py
------------------------------
Legacy LLM routing service (role-based ``LLM_ROLE_CONFIG_JSON`` path).

Active when ``ENABLE_ORCHESTRATED_DOUBT_SOLVER=false``:
  - ``answer_generator_service.generate_answer`` (legacy 7-node graph)
  - ``query_classifier_service.classify_query`` legacy branch

The orchestrated doubt solver path uses ``services.llm.orchestration`` and
``services.doubt_solver.answer_generation_adapter`` instead — not this module.

Rules:
- Graph nodes must not import provider modules directly.
- Provider selection is driven entirely by role config + ENABLE_REAL_LLM flag.
- Secrets (API keys, endpoints) are read inside provider modules — never here.
- Log role, provider, model_label only — never keys or full request content.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from schemas.llm import LlmMessage, LlmRequest, LlmResponse, LlmStreamChunk
from services.llm.providers.azure_openai_provider import AzureOpenAIProvider
from services.llm.providers.base import BaseLlmProvider
from services.llm.providers.errors import LlmConfigurationError
from services.llm.providers.mock_provider import MockProvider
from services.llm.providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PROVIDER_MAP: dict[str, type[BaseLlmProvider]] = {
    "mock": MockProvider,
    "azure_openai": AzureOpenAIProvider,
    "openai": OpenAIProvider,
}


def _get_provider(provider_name: str) -> BaseLlmProvider:
    cls = _PROVIDER_MAP.get(provider_name)
    if cls is None:
        raise LlmConfigurationError(
            f"Unknown provider {provider_name!r}. "
            f"Supported: {list(_PROVIDER_MAP.keys())}"
        )
    return cls()


def _coerce_messages(messages: list[LlmMessage] | list[dict]) -> list[LlmMessage]:
    """Accept either LlmMessage objects or plain dicts and return LlmMessage list."""
    result: list[LlmMessage] = []
    for m in messages:
        if isinstance(m, LlmMessage):
            result.append(m)
        else:
            result.append(LlmMessage.model_validate(m))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(
    role: str,
    messages: list[LlmMessage] | list[dict],
) -> LlmResponse:
    """Generate a complete LLM response for the given role and messages.

    When ENABLE_REAL_LLM=false (default), the mock provider is always used
    regardless of the role config.  Set ENABLE_REAL_LLM=true to use the
    provider configured in LLM_ROLE_CONFIG_JSON.

    Args:
        role:     Named role (maps to a config entry in LLM_ROLE_CONFIG_JSON).
        messages: Conversation messages as LlmMessage objects or plain dicts.

    Returns:
        Provider-neutral LlmResponse.

    Raises:
        LlmConfigurationError: If config is missing or the provider is unknown.
        LlmGenerationError:    If the provider call fails.
    """
    # Import deferred to ensure dotenv has loaded before config is read.
    from config import get_llm_role_config  # noqa: PLC0415

    config = get_llm_role_config(role)
    provider = _get_provider(config.provider)
    coerced = _coerce_messages(messages)
    request = LlmRequest(role=role, messages=coerced)

    logger.info(
        "model_router.generate  role=%s  provider=%s  model_label=%s",
        role,
        config.provider,
        config.model_label,
    )
    return provider.generate(request, config)


def stream(
    role: str,
    messages: list[LlmMessage] | list[dict],
) -> Iterator[LlmStreamChunk]:
    """Stream LLM response chunks for the given role and messages.

    Same provider-selection rules as generate().

    Args:
        role:     Named role (maps to a config entry in LLM_ROLE_CONFIG_JSON).
        messages: Conversation messages as LlmMessage objects or plain dicts.

    Yields:
        LlmStreamChunk instances. The last chunk has is_final=True.

    Raises:
        LlmProviderError:      If the chosen provider does not support streaming.
        LlmConfigurationError: If config is missing or provider is unknown.
        LlmGenerationError:    If the provider call fails during streaming.
    """
    from config import get_llm_role_config  # noqa: PLC0415

    config = get_llm_role_config(role)
    provider = _get_provider(config.provider)
    coerced = _coerce_messages(messages)
    request = LlmRequest(role=role, messages=coerced)

    logger.info(
        "model_router.stream  role=%s  provider=%s  model_label=%s",
        role,
        config.provider,
        config.model_label,
    )
    yield from provider.stream(request, config)
