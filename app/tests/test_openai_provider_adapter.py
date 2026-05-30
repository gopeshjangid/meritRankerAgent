"""
app/tests/test_openai_provider_adapter.py
------------------------------------------
Unit tests for OpenAIProviderAdapter (Part 6).

Tests cover:
- Requires api_key
- Rejects missing model_id
- Converts LlmMessage list to message dicts correctly
- Calls fake client with model_id, messages, temperature, max_tokens
- Returns normalized ModelExecutionResult
- Extracts finish_reason if provided
- Extracts token usage if provided
- Missing content raises LlmProviderResponseError
- Provider exception raises LlmProviderExecutionError
- No API key in error/log/metadata
- No env read
- No network
- No importlib.reload()
"""

from __future__ import annotations

import textwrap
import types
from pathlib import Path

import pytest

from schemas.llm import LlmMessage
from schemas.llm_orchestration import ModelExecutionResult, ProviderExecutionRequest
from schemas.llm_routing import RouteDecision
from services.llm_orchestration.config_registry import LlmConfigRegistry
from services.llm_orchestration.model_config_resolver import ModelConfigResolver
from services.llm_providers.errors import (
    LlmProviderConfigurationError,
    LlmProviderExecutionError,
    LlmProviderResponseError,
)
from services.llm_providers.openai_provider import OpenAIProviderAdapter
from services.secrets.provider_credentials import ProviderCredentials

# ---------------------------------------------------------------------------
# Test YAML config with openai provider
# ---------------------------------------------------------------------------

_OPENAI_YAML = textwrap.dedent("""\
    version: 1
    routes:
      general:
        generator:
          default:
            model: gpt4o_default
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
      gpt4o_default:
        provider: openai
        provider_profile: openai_primary
        model_id: gpt-4o
        model_label: gpt-4o-default
        cost_tier: medium
        supports_streaming: false
        supports_thinking: false
        timeout_seconds: 30
    provider_profiles:
      local_mock:
        provider: mock
      openai_primary:
        provider: openai
        api_key_env: OPENAI_API_KEY
""")


def _registry(tmp_path: Path) -> LlmConfigRegistry:
    yaml_path = tmp_path / "llm_orchestration.yaml"
    yaml_path.write_text(_OPENAI_YAML, encoding="utf-8")
    return LlmConfigRegistry(yaml_path=yaml_path)


def _route_decision() -> RouteDecision:
    return RouteDecision(
        route_id="general.generator.default",
        subject="general",
        task_role="generator",
        difficulty="default",
        model="gpt4o_default",
        prompt="subjects/general_generator.md",
        temperature=0.3,
        max_tokens=800,
        provider_options={},
        fallback_attempts=[],
        route_source="exact",
    )


def _messages() -> list[LlmMessage]:
    return [
        LlmMessage(role="system", content="You are a helpful tutor."),
        LlmMessage(role="user", content="Explain photosynthesis."),
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


def _openai_credentials() -> ProviderCredentials:
    return ProviderCredentials(provider="openai", api_key="fake-test-key")


# ---------------------------------------------------------------------------
# Fake client helpers
# ---------------------------------------------------------------------------


def _fake_completion(
    content: str = "Test answer.",
    finish_reason: str = "stop",
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> object:
    usage = types.SimpleNamespace(prompt_tokens=input_tokens, completion_tokens=output_tokens)
    message = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=message, finish_reason=finish_reason)
    return types.SimpleNamespace(choices=[choice], usage=usage)


class FakeOpenAIClient:
    """Fake openai.OpenAI-like client for unit testing."""

    def __init__(
        self, completion: object | None = None, raise_exc: Exception | None = None
    ) -> None:
        self._completion = completion
        self._raise_exc = raise_exc
        self.received_kwargs: dict = {}

        def _create(**kwargs):  # noqa: ANN202
            self.received_kwargs = kwargs
            if self._raise_exc is not None:
                raise self._raise_exc
            return self._completion

        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=_create)
        )


def _factory(client: FakeOpenAIClient):  # noqa: ANN202
    return lambda _creds: client


# ---------------------------------------------------------------------------
# Credential validation
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterCredentials:
    def test_missing_api_key_raises_config_error(self, tmp_path: Path) -> None:
        adapter = OpenAIProviderAdapter()
        creds = ProviderCredentials(provider="openai")  # api_key=None
        with pytest.raises(LlmProviderConfigurationError, match="api_key"):
            adapter.generate(request=_make_request(tmp_path), credentials=creds)

    def test_error_message_does_not_contain_key_value(self, tmp_path: Path) -> None:
        adapter = OpenAIProviderAdapter()
        creds = ProviderCredentials(provider="openai")
        with pytest.raises(LlmProviderConfigurationError) as exc_info:
            adapter.generate(request=_make_request(tmp_path), credentials=creds)
        assert "sk-" not in str(exc_info.value)
        assert "fake-test-key" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# model_id validation
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterModelId:
    def test_missing_model_id_raises_config_error(self, tmp_path: Path) -> None:
        """Provider adaptor must reject missing model_id (not route alias)."""
        # Build a config without model_id (mock provider doesn't require it, but openai does)
        no_model_id_yaml = textwrap.dedent("""\
            version: 1
            routes:
              general:
                generator:
                  default:
                    model: gpt4o_no_id
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
              gpt4o_no_id:
                provider: mock
                provider_profile: local_mock
                model_label: gpt4o-no-id
                cost_tier: none
                supports_streaming: false
                supports_thinking: false
                timeout_seconds: 1
            provider_profiles:
              local_mock:
                provider: mock
        """)
        yaml_path = tmp_path / "llm_orchestration.yaml"
        yaml_path.write_text(no_model_id_yaml, encoding="utf-8")
        registry = LlmConfigRegistry(yaml_path=yaml_path)
        resolver = ModelConfigResolver(registry=registry)

        rd = RouteDecision(
            route_id="general.generator.default",
            subject="general",
            task_role="generator",
            difficulty="default",
            model="gpt4o_no_id",
            prompt="subjects/general_generator.md",
            temperature=0.3,
            max_tokens=800,
            provider_options={},
            fallback_attempts=[],
            route_source="exact",
        )
        model_resolution = resolver.resolve(rd)
        request = ProviderExecutionRequest(
            route_decision=rd,
            model_resolution=model_resolution,
            messages=_messages(),
            temperature=0.3,
            max_tokens=800,
        )

        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        creds = _openai_credentials()

        with pytest.raises(LlmProviderConfigurationError, match="model_id"):
            adapter.generate(request=request, credentials=creds)


# ---------------------------------------------------------------------------
# Successful generate
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterGenerate:
    def test_returns_model_execution_result(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion("Great answer."))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert isinstance(result, ModelExecutionResult)

    def test_provider_is_openai(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion("Answer."))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.provider == "openai"

    def test_content_is_returned(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion("Photosynthesis answer."))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.content == "Photosynthesis answer."

    def test_model_is_route_alias(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion("Answer."))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.model == "gpt4o_default"

    def test_calls_client_with_model_id(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        assert client.received_kwargs["model"] == "gpt-4o"

    def test_calls_client_with_temperature(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        assert client.received_kwargs["temperature"] == pytest.approx(0.3)

    def test_calls_client_with_max_tokens(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        assert client.received_kwargs["max_tokens"] == 800

    def test_calls_client_with_messages(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        msgs = client.received_kwargs["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are a helpful tutor."
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "Explain photosynthesis."


# ---------------------------------------------------------------------------
# finish_reason and token extraction
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterResponseParsing:
    def test_finish_reason_extracted(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion(finish_reason="length"))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.finish_reason == "length"

    def test_input_tokens_extracted(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion(input_tokens=42))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.input_tokens == 42

    def test_output_tokens_extracted(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion(output_tokens=17))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.output_tokens == 17

    def test_missing_usage_returns_none(self, tmp_path: Path) -> None:
        # completion without usage attribute
        message = types.SimpleNamespace(content="Answer.")
        choice = types.SimpleNamespace(message=message, finish_reason="stop")
        completion_no_usage = types.SimpleNamespace(choices=[choice])
        client = FakeOpenAIClient(completion=completion_no_usage)
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.input_tokens is None
        assert result.output_tokens is None


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterErrors:
    def test_empty_content_raises_response_error(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion(content=""))
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        with pytest.raises(LlmProviderResponseError):
            adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())

    def test_none_content_raises_response_error(self, tmp_path: Path) -> None:
        message = types.SimpleNamespace(content=None)
        choice = types.SimpleNamespace(message=message, finish_reason="stop")
        completion = types.SimpleNamespace(choices=[choice], usage=None)
        client = FakeOpenAIClient(completion=completion)
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        with pytest.raises(LlmProviderResponseError):
            adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())

    def test_provider_exception_raises_execution_error(self, tmp_path: Path) -> None:
        sdk_exc = RuntimeError("connection refused")
        client = FakeOpenAIClient(raise_exc=sdk_exc)
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        with pytest.raises(LlmProviderExecutionError):
            adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())

    def test_execution_error_wraps_original(self, tmp_path: Path) -> None:
        sdk_exc = RuntimeError("timeout")
        client = FakeOpenAIClient(raise_exc=sdk_exc)
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        with pytest.raises(LlmProviderExecutionError) as exc_info:
            adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        assert exc_info.value.__cause__ is sdk_exc

    def test_execution_error_does_not_include_api_key(self, tmp_path: Path) -> None:
        sdk_exc = RuntimeError("auth failed")
        client = FakeOpenAIClient(raise_exc=sdk_exc)
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        with pytest.raises(LlmProviderExecutionError) as exc_info:
            adapter.generate(request=_make_request(tmp_path), credentials=_openai_credentials())
        assert "fake-test-key" not in str(exc_info.value)
        assert "sk-" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Metadata safety
# ---------------------------------------------------------------------------


class TestOpenAIProviderAdapterMetadata:
    def test_metadata_does_not_contain_api_key(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        for v in result.metadata.values():
            assert "fake-test-key" not in str(v)

    def test_metadata_does_not_contain_messages(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert "messages" not in result.metadata

    def test_metadata_contains_model_label(self, tmp_path: Path) -> None:
        client = FakeOpenAIClient(completion=_fake_completion())
        adapter = OpenAIProviderAdapter(client_factory=_factory(client))
        result = adapter.generate(
            request=_make_request(tmp_path),
            credentials=_openai_credentials(),
        )
        assert result.metadata.get("model_label") == "gpt-4o-default"


# ---------------------------------------------------------------------------
# Import safety (no importlib.reload)
# ---------------------------------------------------------------------------


class TestImportSafety:
    def test_import_openai_provider_module(self) -> None:
        import services.llm_providers.openai_provider  # noqa: F401
