"""
app/tests/test_llm_orchestration_dry_run.py
---------------------------------------------
Tests for Part 7: Controlled LLM Orchestration Dry-Run.

Verifies that ``run_mock_orchestration_dry_run`` exercises the full wired
orchestration stack — RegistryBackedModelExecutor → ProviderAdapterExecutor
→ MockProviderAdapter — without making any real provider calls, network I/O,
AWS calls, or environment-variable reads.

Test coverage:
1.  Dry-run returns a LlmDryRunResult (correct type).
2.  result.provider is "mock".
3.  OpenAI and Azure adapters are never instantiated.
4.  No environment variables are read (no OPENAI_API_KEY or AZURE keys needed).
5.  No network calls occur (socket-level assertion).
6.  No AWS / boto3 calls occur.
7.  result.safe_metadata does not contain prompt / messages / query / context keys.
8.  result.safe_metadata contains only expected safe keys.
9.  result.answer_source is "mock" (LlmOrchestrator sets this for mock provider).
10. result.model matches the safe_mock alias from the production YAML registry.
11. result.route_id is the synthetic dry-run route id.
12. result.content equals the MockProviderAdapter's fixed content.
13. Empty query raises LlmOrchestratorError.
14. Context is accepted and does not appear in safe_metadata.
15. Production YAML general.generator.default route still points to gemini (not safe_mock).
"""

from __future__ import annotations

import socket
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.llm_orchestration.config_registry import LlmConfigRegistry
from services.llm_orchestration.dry_run import (
    LlmDryRunInput,
    LlmDryRunResult,
    run_mock_orchestration_dry_run,
)
from services.llm_orchestration.errors import LlmOrchestratorError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNSAFE_METADATA_KEYS = frozenset(
    {
        "prompt",
        "system_prompt",
        "user_prompt",
        "messages",
        "query",
        "context",
        "api_key",
        "api_key_env",
        "endpoint_env",
        "api_version_env",
        "base_url_env",
        "credential_ref",
        "secret",
        "credential",
    }
)


def _make_input(**kwargs: Any) -> LlmDryRunInput:
    defaults: dict[str, Any] = {"query": "What is 10% of 200?"}
    return LlmDryRunInput(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Test 1 — dry-run returns LlmDryRunResult
# ---------------------------------------------------------------------------


def test_dry_run_returns_llm_dry_run_result() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    assert isinstance(result, LlmDryRunResult)


# ---------------------------------------------------------------------------
# Test 2 — provider is "mock"
# ---------------------------------------------------------------------------


def test_dry_run_provider_is_mock() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    assert result.provider == "mock"


# ---------------------------------------------------------------------------
# Test 3 — OpenAI and Azure adapters are never instantiated
# ---------------------------------------------------------------------------


def test_dry_run_does_not_instantiate_real_provider_adapters() -> None:
    """Verify that OpenAIProviderAdapter and AzureOpenAIProviderAdapter are
    never constructed during a mock dry-run."""
    with (
        patch(
            "services.llm_providers.openai_provider.OpenAIProviderAdapter.__init__",
            side_effect=AssertionError("OpenAI adapter must not be instantiated in dry-run"),
        ),
        patch(
            "services.llm_providers.azure_openai_provider.AzureOpenAIProviderAdapter.__init__",
            side_effect=AssertionError("Azure adapter must not be instantiated in dry-run"),
        ),
    ):
        result = run_mock_orchestration_dry_run(_make_input())
    assert result.provider == "mock"


# ---------------------------------------------------------------------------
# Test 4 — no env var reads (OPENAI_API_KEY / AZURE keys not required)
# ---------------------------------------------------------------------------


def test_dry_run_does_not_require_real_provider_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all real provider env vars and verify dry-run still succeeds."""
    for var in (
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    result = run_mock_orchestration_dry_run(_make_input())
    assert result.provider == "mock"


# ---------------------------------------------------------------------------
# Test 5 — no network calls
# ---------------------------------------------------------------------------


def test_dry_run_makes_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch socket.socket.connect to fail on any call.

    If the dry-run ever attempts a network connection, this test will fail
    with a clear assertion rather than a silent timeout.
    """

    def _no_connect(self: socket.socket, *args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            f"Dry-run must not make any network calls, but socket.connect was called "
            f"with args={args!r}"
        )

    monkeypatch.setattr(socket.socket, "connect", _no_connect)

    result = run_mock_orchestration_dry_run(_make_input())
    assert result.provider == "mock"


# ---------------------------------------------------------------------------
# Test 6 — no AWS / boto3 calls
# ---------------------------------------------------------------------------


def test_dry_run_makes_no_boto3_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify boto3 is not imported or called during the dry-run."""
    import sys

    # Remove boto3 from sys.modules if present, then replace with a fail-sentinel.
    sentinel = MagicMock(name="boto3-sentinel")
    sentinel.client = MagicMock(
        side_effect=AssertionError("boto3.client must not be called in dry-run")
    )
    sentinel.resource = MagicMock(
        side_effect=AssertionError("boto3.resource must not be called in dry-run")
    )
    sys.modules.pop("boto3", None)
    monkeypatch.setitem(sys.modules, "boto3", sentinel)

    result = run_mock_orchestration_dry_run(_make_input())
    assert result.provider == "mock"

    # Restore
    sys.modules.pop("boto3", None)


# ---------------------------------------------------------------------------
# Test 7 — safe_metadata does not contain unsafe keys
# ---------------------------------------------------------------------------


def test_dry_run_safe_metadata_has_no_unsafe_keys() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    present_unsafe = _UNSAFE_METADATA_KEYS & result.safe_metadata.keys()
    assert not present_unsafe, (
        f"safe_metadata must not contain unsafe keys, found: {present_unsafe}"
    )


# ---------------------------------------------------------------------------
# Test 8 — safe_metadata contains expected safe keys only
# ---------------------------------------------------------------------------


def test_dry_run_safe_metadata_contains_expected_keys() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    expected_keys = {
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
    missing = expected_keys - result.safe_metadata.keys()
    assert not missing, f"safe_metadata missing expected keys: {missing}"
    extra = result.safe_metadata.keys() - expected_keys
    assert not extra, f"safe_metadata has unexpected keys: {extra}"


# ---------------------------------------------------------------------------
# Test 9 — answer_source is "mock" (LlmOrchestrator)
# ---------------------------------------------------------------------------


def test_dry_run_answer_source_is_mock() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    assert result.answer_source == "mock"


# ---------------------------------------------------------------------------
# Test 10 — result.model matches safe_mock alias from production YAML
# ---------------------------------------------------------------------------


def test_dry_run_model_matches_safe_mock_registry_alias() -> None:
    """RegistryBackedModelExecutor resolves safe_mock from the production YAML.

    The model alias returned in the result must be "safe_mock" — the value set
    in the ModelExecutionResult by the MockProviderAdapter path through the
    RegistryBackedModelExecutor.
    """
    result = run_mock_orchestration_dry_run(_make_input())
    # The executor sets model from the resolved model alias.
    assert result.model == "safe_mock"


# ---------------------------------------------------------------------------
# Test 11 — route_id is the synthetic dry-run route id
# ---------------------------------------------------------------------------


def test_dry_run_route_id_is_synthetic() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    assert result.route_id == "dry_run.generator.default"


# ---------------------------------------------------------------------------
# Test 12 — content equals MockProviderAdapter's fixed content
# ---------------------------------------------------------------------------


def test_dry_run_content_from_mock_provider_adapter() -> None:
    result = run_mock_orchestration_dry_run(_make_input())
    assert result.content == "Dry-run mock response."


# ---------------------------------------------------------------------------
# Test 13 — empty query raises LlmOrchestratorError
# ---------------------------------------------------------------------------


def test_dry_run_empty_query_raises() -> None:
    with pytest.raises((ValueError, LlmOrchestratorError)):
        # Pydantic validation catches min_length=1 before the orchestrator,
        # but we also check at the orchestrator layer.
        run_mock_orchestration_dry_run(LlmDryRunInput.model_construct(query=""))


def test_dry_run_whitespace_query_raises() -> None:
    """Whitespace-only query bypasses Pydantic (via model_construct) and fails
    at the orchestrator layer with LlmOrchestratorError."""
    # model_construct bypasses Pydantic validation so the whitespace reaches
    # the orchestrator's empty-query guard.
    bad_input = LlmDryRunInput.model_construct(
        query="   ",
        subject="general",
        difficulty="default",
        intent="explain",
        context=None,
    )
    with pytest.raises(LlmOrchestratorError):
        run_mock_orchestration_dry_run(bad_input)


# ---------------------------------------------------------------------------
# Test 14 — context accepted and never appears in safe_metadata
# ---------------------------------------------------------------------------


def test_dry_run_context_accepted_does_not_leak_to_metadata() -> None:
    result = run_mock_orchestration_dry_run(
        _make_input(
            query="What is the speed of light?",
            context="Speed of light = 299,792,458 m/s.",
        )
    )
    assert result.provider == "mock"
    assert "context" not in result.safe_metadata


# ---------------------------------------------------------------------------
# Test 15 — production general.generator.default still points to gemini
# ---------------------------------------------------------------------------


def test_production_general_route_not_polluted_by_dry_run() -> None:
    """Verify the production routes were not changed to safe_mock.

    ``general.generator.default`` must still resolve to the real model
    (general_fast_generator or equivalent), proving that the dry-run's
    synthetic RouteDecision did not modify the YAML.
    """
    registry = LlmConfigRegistry()  # loads production YAML
    route = registry.get_route("general", "generator", "default")
    assert route is not None, "Production route general.generator.default must exist"
    # The real route uses gemini — never safe_mock.
    assert route.model != "safe_mock", (
        "Production route general.generator.default must not point to safe_mock. "
        f"Found model={route.model!r}. Dry-run should NOT modify production YAML routes."
    )
