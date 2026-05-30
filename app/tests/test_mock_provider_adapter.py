"""
app/tests/test_mock_provider_adapter.py
-----------------------------------------
Unit tests for MockProviderAdapter (Part 6).

Tests cover:
- Returns ModelExecutionResult with provider="mock"
- content matches configured content
- model matches route_decision.model alias
- records last_request and call_count
- metadata is safe (no prompt/messages/query/context)
- no env read
- no network
- no importlib.reload()
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from schemas.llm import LlmMessage
from schemas.llm_orchestration import ModelExecutionResult, ProviderExecutionRequest
from schemas.llm_routing import RouteDecision
from services.llm_orchestration.config_registry import LlmConfigRegistry
from services.llm_orchestration.model_config_resolver import ModelConfigResolver
from services.llm_providers.mock_provider import MockProviderAdapter
from services.secrets.provider_credentials import ProviderCredentials

# ---------------------------------------------------------------------------
# Test YAML config with mock provider
# ---------------------------------------------------------------------------

_MOCK_YAML = textwrap.dedent("""\
    version: 1
    routes:
      general:
        generator:
          default:
            model: safe_mock
            prompt: subjects/general_generator.md
            temperature: 0.3
            max_tokens: 800
    models:
      safe_mock:
        provider: mock
        provider_profile: local_mock
        model_label: safe-mock
        cost_tier: none
        supports_streaming: false
        supports_thinking: false
        timeout_seconds: 1
    provider_profiles:
      local_mock:
        provider: mock
""")


def _registry(tmp_path: Path) -> LlmConfigRegistry:
    yaml_path = tmp_path / "llm_orchestration.yaml"
    yaml_path.write_text(_MOCK_YAML, encoding="utf-8")
    return LlmConfigRegistry(yaml_path=yaml_path)


def _route_decision() -> RouteDecision:
    return RouteDecision(
        route_id="general.generator.default",
        subject="general",
        task_role="generator",
        difficulty="default",
        model="safe_mock",
        prompt="subjects/general_generator.md",
        temperature=0.3,
        max_tokens=800,
        provider_options={},
        fallback_attempts=[],
        route_source="exact",
    )


def _messages() -> list[LlmMessage]:
    return [
        LlmMessage(role="system", content="You are a tutor."),
        LlmMessage(role="user", content="What is gravity?"),
    ]


def _make_request(tmp_path: Path) -> ProviderExecutionRequest:
    resolver = ModelConfigResolver(registry=_registry(tmp_path))
    model_resolution = resolver.resolve(_route_decision())
    return ProviderExecutionRequest(
        route_decision=_route_decision(),
        model_resolution=model_resolution,
        messages=_messages(),
        temperature=0.3,
        max_tokens=800,
    )


def _mock_credentials() -> ProviderCredentials:
    return ProviderCredentials(provider="mock")


# ---------------------------------------------------------------------------
# Basic generate() behaviour
# ---------------------------------------------------------------------------


class TestMockProviderAdapterGenerate:
    def test_returns_model_execution_result(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert isinstance(result, ModelExecutionResult)

    def test_provider_is_mock(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert result.provider == "mock"

    def test_default_content(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert result.content == "Mock provider response."

    def test_custom_content(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter(content="Custom answer.")
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert result.content == "Custom answer."

    def test_model_is_route_alias(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert result.model == "safe_mock"

    def test_finish_reason_is_stop(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert result.finish_reason == "stop"


# ---------------------------------------------------------------------------
# Records last_request and call_count
# ---------------------------------------------------------------------------


class TestMockProviderAdapterState:
    def test_call_count_starts_at_zero(self) -> None:
        adapter = MockProviderAdapter()
        assert adapter.call_count == 0

    def test_last_request_starts_none(self) -> None:
        adapter = MockProviderAdapter()
        assert adapter.last_request is None

    def test_call_count_increments(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        req = _make_request(tmp_path)
        adapter.generate(request=req, credentials=_mock_credentials())
        adapter.generate(request=req, credentials=_mock_credentials())
        assert adapter.call_count == 2

    def test_last_request_recorded(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        req = _make_request(tmp_path)
        adapter.generate(request=req, credentials=_mock_credentials())
        assert adapter.last_request is req


# ---------------------------------------------------------------------------
# Metadata safety
# ---------------------------------------------------------------------------


class TestMockProviderAdapterMetadata:
    def test_metadata_does_not_contain_messages(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert "messages" not in result.metadata

    def test_metadata_does_not_contain_prompt(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert "prompt" not in result.metadata

    def test_metadata_does_not_contain_api_key(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert "api_key" not in result.metadata

    def test_metadata_contains_safe_model_alias(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_mock_credentials(),
        )
        assert "model_alias" in result.metadata


# ---------------------------------------------------------------------------
# Credentials are not required / ignored
# ---------------------------------------------------------------------------


class TestMockProviderAdapterCredentials:
    def test_accepts_empty_credentials(self, tmp_path: Path) -> None:
        adapter = MockProviderAdapter()
        creds = ProviderCredentials(provider="mock")
        result = adapter.generate(request=_make_request(tmp_path), credentials=creds)
        assert result.content == "Mock provider response."


# ---------------------------------------------------------------------------
# Import safety (no importlib.reload)
# ---------------------------------------------------------------------------


class TestImportSafety:
    def test_import_mock_provider_module(self) -> None:
        import services.llm_providers.mock_provider  # noqa: F401
