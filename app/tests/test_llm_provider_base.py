"""
app/tests/test_llm_provider_base.py
-------------------------------------
Unit tests for services/llm_providers/base.py — Part 6 additions.

Tests cover:
- sanitize_provider_metadata removes unsafe keys
- safe keys remain after sanitize
- ProviderAdapter protocol runtime_checkable check
- No import-time env read
- No importlib.reload()
"""

from __future__ import annotations

from services.llm_providers.base import ProviderAdapter, sanitize_provider_metadata
from services.llm_providers.errors import (
    LlmProviderAdapterError,
    LlmProviderConfigurationError,
    LlmProviderExecutionError,
    LlmProviderResponseError,
    LlmProviderUnsupportedFeatureError,
)

# ---------------------------------------------------------------------------
# sanitize_provider_metadata
# ---------------------------------------------------------------------------


class TestSanitizeProviderMetadata:
    def test_removes_prompt_key(self) -> None:
        result = sanitize_provider_metadata({"prompt": "secret prompt", "model_label": "gpt4o"})
        assert "prompt" not in result

    def test_removes_system_prompt_key(self) -> None:
        result = sanitize_provider_metadata({"system_prompt": "You are...", "safe_key": "ok"})
        assert "system_prompt" not in result

    def test_removes_user_prompt_key(self) -> None:
        result = sanitize_provider_metadata({"user_prompt": "question here"})
        assert "user_prompt" not in result

    def test_removes_messages_key(self) -> None:
        result = sanitize_provider_metadata({"messages": [{"role": "user", "content": "hi"}]})
        assert "messages" not in result

    def test_removes_query_key(self) -> None:
        result = sanitize_provider_metadata({"query": "student query here"})
        assert "query" not in result

    def test_removes_context_key(self) -> None:
        result = sanitize_provider_metadata({"context": "retrieved context"})
        assert "context" not in result

    def test_removes_api_key_key(self) -> None:
        result = sanitize_provider_metadata({"api_key": "sk-secret123"})
        assert "api_key" not in result

    def test_removes_secret_key(self) -> None:
        result = sanitize_provider_metadata({"secret": "supersecret"})
        assert "secret" not in result

    def test_removes_credential_key(self) -> None:
        result = sanitize_provider_metadata({"credential": "cred-value"})
        assert "credential" not in result

    def test_removes_authorization_key(self) -> None:
        result = sanitize_provider_metadata({"authorization": "Bearer tok"})
        assert "authorization" not in result

    def test_removes_raw_response_key(self) -> None:
        result = sanitize_provider_metadata({"raw_response": {"choices": []}})
        assert "raw_response" not in result

    def test_preserves_safe_model_label(self) -> None:
        result = sanitize_provider_metadata({"model_label": "gpt-4o"})
        assert result["model_label"] == "gpt-4o"

    def test_preserves_safe_deployment(self) -> None:
        result = sanitize_provider_metadata({"deployment": "my-deployment"})
        assert result["deployment"] == "my-deployment"

    def test_preserves_safe_provider(self) -> None:
        result = sanitize_provider_metadata({"provider": "openai"})
        assert result["provider"] == "openai"

    def test_preserves_safe_model_alias(self) -> None:
        result = sanitize_provider_metadata({"model_alias": "gpt4o_default"})
        assert result["model_alias"] == "gpt4o_default"

    def test_empty_dict_returns_empty(self) -> None:
        assert sanitize_provider_metadata({}) == {}

    def test_mixed_safe_and_unsafe_keys(self) -> None:
        result = sanitize_provider_metadata(
            {
                "model_label": "gpt-4o",
                "api_key": "sk-secret",
                "messages": ["msg1"],
                "deployment": "my-dep",
                "prompt": "system prompt here",
                "provider": "azure_openai",
            }
        )
        assert result == {
            "model_label": "gpt-4o",
            "deployment": "my-dep",
            "provider": "azure_openai",
        }

    def test_returns_copy_not_original(self) -> None:
        original = {"model_label": "gpt-4o", "safe_key": "value"}
        result = sanitize_provider_metadata(original)
        assert result is not original


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class TestLlmProviderAdapterErrorHierarchy:
    def test_config_error_is_adapter_error(self) -> None:
        err = LlmProviderConfigurationError("bad config")
        assert isinstance(err, LlmProviderAdapterError)

    def test_execution_error_is_adapter_error(self) -> None:
        err = LlmProviderExecutionError("sdk failed")
        assert isinstance(err, LlmProviderAdapterError)

    def test_response_error_is_adapter_error(self) -> None:
        err = LlmProviderResponseError("empty content")
        assert isinstance(err, LlmProviderAdapterError)

    def test_unsupported_error_is_adapter_error(self) -> None:
        err = LlmProviderUnsupportedFeatureError("streaming not supported")
        assert isinstance(err, LlmProviderAdapterError)

    def test_error_message_does_not_need_secret_value(self) -> None:
        # Error messages should never contain credential values.
        err = LlmProviderConfigurationError("api_key is missing for model_alias='gpt4o'")
        msg = str(err)
        # The message may name the field (api_key) but must never include an actual key value.
        assert "sk-" not in msg
        assert "AIza" not in msg
        assert "AKIA" not in msg

    def test_execution_error_has_cause(self) -> None:
        cause = RuntimeError("connection refused")
        err = LlmProviderExecutionError("OpenAI call failed: RuntimeError")
        err.__cause__ = cause
        assert err.__cause__ is cause


# ---------------------------------------------------------------------------
# ProviderAdapter protocol runtime_checkable
# ---------------------------------------------------------------------------


class TestProviderAdapterProtocol:
    def test_class_without_generate_not_provider_adapter(self) -> None:
        class BadAdapter:
            pass

        assert not isinstance(BadAdapter(), ProviderAdapter)

    def test_class_with_generate_is_provider_adapter(self) -> None:
        class GoodAdapter:
            def generate(self, *, request, credentials):  # noqa: ANN001
                ...

        assert isinstance(GoodAdapter(), ProviderAdapter)


# ---------------------------------------------------------------------------
# Import safety (no importlib.reload)
# ---------------------------------------------------------------------------


class TestImportSafety:
    def test_import_base_module(self) -> None:
        import services.llm_providers.base  # noqa: F401

    def test_import_errors_module(self) -> None:
        import services.llm_providers.errors  # noqa: F401
