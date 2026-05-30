"""
app/services/llm_orchestration/dry_run.py
------------------------------------------
Controlled LLM orchestration dry-run — Part 7.

Provides a service-level dry-run that exercises the *full* orchestration chain
using ``MockProviderAdapter`` — no real provider calls, no network I/O, no
environment-variable reads beyond what the production ``local_mock`` profile
already requires (none).

Public API:
    LlmDryRunInput   — Pydantic input model.
    LlmDryRunResult  — Pydantic result model.  safe_metadata never contains
                       prompt / messages / query / context keys.
    run_mock_orchestration_dry_run(input)  →  LlmDryRunResult

Design:
- Uses a synthetic ``RouteDecision`` (route_source="safe_mock", model="safe_mock").
  The ``safe_mock`` model is already declared in the production
  ``app/config/llm/llm_orchestration.yaml`` — no YAML change required.
- Injects ``route_resolver_fn = lambda _: synthetic_route_decision`` into
  ``LlmOrchestrator`` so the production route resolver is never called.
- Uses the production ``PromptResolver`` backed by ``app/prompts/`` — real
  prompt templates are resolved.
- Wires:
    RegistryBackedModelExecutor
    → ProviderAdapterExecutor
    → ProviderAdapterFactory (mock-only adapter map)
    → MockProviderAdapter
- ``local_mock`` provider profile declares no ``api_key_env`` / ``endpoint_env``
  references, so ``EnvSecretResolver`` is never asked for any variable.
- Production YAML routes are not modified; the synthetic RouteDecision is built
  entirely in this module.

Non-goals (deferred):
- OpenAI / Azure smoke path (→ ``app/scripts/smoke_llm_orchestration.py``).
- Provider-level fallback.
- Streaming.
- Graph / answer_generator_service wiring.
- AgentCore Identity / Langfuse.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from schemas.llm_orchestration import OrchestrationResult
from schemas.llm_routing import RouteDecision, RouteRequest
from services.llm.orchestration.model_config_resolver import ModelConfigResolver
from services.llm.orchestration.model_execution import (
    ProviderAdapterExecutor,
    RegistryBackedModelExecutor,
)
from services.llm.orchestration.orchestrator import LlmOrchestrator
from services.llm.orchestration.prompt_resolver import DEFAULT_PROMPT_ROOT, PromptResolver
from services.llm.providers.mock_provider import MockProviderAdapter
from services.llm.providers.provider_factory import ProviderAdapterFactory
from services.secrets.env_secret_resolver import EnvSecretResolver
from services.secrets.provider_credentials import ProviderCredentialResolver

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Model alias in the production YAML that maps to provider=mock, local_mock profile.
_SAFE_MOCK_MODEL: str = "safe_mock"

#: Prompt used for all dry-run calls regardless of subject.
_DRY_RUN_PROMPT: str = "subjects/general_generator.md"

#: Safe metadata keys allowed in LlmDryRunResult.safe_metadata.
_SAFE_METADATA_FIELDS: frozenset[str] = frozenset(
    {
        "model_alias",
        "provider",
        "route_id",
        "answer_source",
        "fallback_used",
        "finish_reason",
        "input_tokens",
        "output_tokens",
        "latency_ms",
    }
)

# ---------------------------------------------------------------------------
# Input / Output Models
# ---------------------------------------------------------------------------


class LlmDryRunInput(BaseModel):
    """Input for the mock orchestration dry-run.

    All fields are optional with safe defaults so callers only need to
    supply a non-empty ``query``.
    """

    query: str = Field(..., min_length=1, description="The question to answer.")
    subject: str = Field(default="general", min_length=1, max_length=64)
    difficulty: str = Field(default="default", max_length=64)
    intent: str | None = Field(default="explain", max_length=128)
    context: str | None = Field(default=None)

    model_config = {"str_strip_whitespace": True}


class LlmDryRunResult(BaseModel):
    """Safe result from the mock orchestration dry-run.

    Intentionally omits prompt content, composed messages, raw query, and
    retrieved context.  ``safe_metadata`` contains only non-sensitive
    operational fields.
    """

    content: str
    route_id: str
    model: str
    provider: str | None
    answer_source: str
    fallback_used: bool
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_synthetic_route_decision(
    *,
    subject: str,
    difficulty: str,
    intent: str | None,
) -> RouteDecision:
    """Return a deterministic RouteDecision pointing to the safe_mock model.

    This route decision is never derived from production YAML routes; it is
    constructed entirely in Python so that:
    - Production routes for real subjects are not changed.
    - The safe_mock model (already in production YAML) is used for model
      config resolution.
    - ``route_source="safe_mock"`` marks the decision as explicitly synthetic.
    """
    return RouteDecision(
        route_id="dry_run.generator.default",
        subject=subject,
        task_role="generator",
        difficulty=difficulty,
        intent=intent,
        exam=None,
        model=_SAFE_MOCK_MODEL,
        prompt=_DRY_RUN_PROMPT,
        overlays=[],
        temperature=0.3,
        max_tokens=800,
        provider_options={},
        fallback_attempts=[],
        route_source="safe_mock",
    )


def _build_orchestrator() -> LlmOrchestrator:
    """Wire the full mock orchestration stack and return a ready orchestrator.

    Stack:
        MockProviderAdapter
        ↑
        ProviderAdapterFactory (mock-only adapter map)
        ↑
        EnvSecretResolver + ProviderCredentialResolver
        ↑
        ProviderAdapterExecutor
        ↑
        RegistryBackedModelExecutor (production ModelConfigResolver → safe_mock)

    No route_resolver_fn is set here; it is injected per-call in
    ``run_mock_orchestration_dry_run`` to pass the synthetic RouteDecision.
    """
    mock_adapter = MockProviderAdapter(content="Dry-run mock response.")
    provider_factory = ProviderAdapterFactory(adapter_map={"mock": mock_adapter})

    secret_resolver = EnvSecretResolver()
    credential_resolver = ProviderCredentialResolver(secret_resolver=secret_resolver)

    adapter_executor = ProviderAdapterExecutor(
        credential_resolver=credential_resolver,
        provider_factory=provider_factory,
    )
    model_executor = RegistryBackedModelExecutor(
        provider_executor=adapter_executor,
        model_config_resolver=ModelConfigResolver(),  # reads production YAML
    )
    prompt_resolver = PromptResolver(prompt_root=DEFAULT_PROMPT_ROOT)

    return LlmOrchestrator(
        model_executor=model_executor,
        prompt_resolver=prompt_resolver,
        # route_resolver_fn is injected per-call via the orchestrator's
        # generate() override path — set below when building the lambda.
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_mock_orchestration_dry_run(input: LlmDryRunInput) -> LlmDryRunResult:
    """Run the full orchestration stack end-to-end with MockProviderAdapter.

    No real provider calls.  No network I/O.  No environment variable reads.
    No graph dependency.  No AWS calls.

    Args:
        input: Validated ``LlmDryRunInput``.

    Returns:
        ``LlmDryRunResult`` with safe metadata only.

    Raises:
        LlmOrchestratorError: If ``input.query`` is empty (validated by Pydantic,
                               but the orchestrator also enforces this).
        LlmOrchestrationError: If the orchestrator encounters an unexpected error.
    """
    synthetic_route_decision = _build_synthetic_route_decision(
        subject=input.subject,
        difficulty=input.difficulty,
        intent=input.intent,
    )

    # Inject the synthetic route decision as the resolver function.
    # The orchestrator calls route_resolver_fn(route_request) — the lambda
    # always returns our pre-built RouteDecision, ignoring the request.
    mock_adapter = MockProviderAdapter(content="Dry-run mock response.")
    provider_factory = ProviderAdapterFactory(adapter_map={"mock": mock_adapter})

    secret_resolver = EnvSecretResolver()
    credential_resolver = ProviderCredentialResolver(secret_resolver=secret_resolver)

    adapter_executor = ProviderAdapterExecutor(
        credential_resolver=credential_resolver,
        provider_factory=provider_factory,
    )
    model_executor = RegistryBackedModelExecutor(
        provider_executor=adapter_executor,
        model_config_resolver=ModelConfigResolver(),
    )
    prompt_resolver = PromptResolver(prompt_root=DEFAULT_PROMPT_ROOT)

    orchestrator = LlmOrchestrator(
        model_executor=model_executor,
        route_resolver_fn=lambda _route_req: synthetic_route_decision,
        prompt_resolver=prompt_resolver,
    )

    route_request = RouteRequest(
        request_id=f"dry-run-{uuid.uuid4().hex[:12]}",
        subject=input.subject,
        task_role="generator",
        difficulty=input.difficulty,
        intent=input.intent,
        exam=None,
    )

    result: OrchestrationResult = orchestrator.generate(
        route_request=route_request,
        query=input.query,
        context=input.context,
    )

    safe_metadata: dict[str, Any] = {
        "model_alias": result.model,
        "provider": result.provider,
        "route_id": result.route_decision.route_id,
        "answer_source": result.answer_source,
        "fallback_used": result.fallback_used,
        "finish_reason": result.finish_reason,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_ms": result.latency_ms,
    }

    return LlmDryRunResult(
        content=result.content,
        route_id=result.route_decision.route_id,
        model=result.model,
        provider=result.provider,
        answer_source=result.answer_source,
        fallback_used=result.fallback_used,
        safe_metadata=safe_metadata,
    )
