"""
app/tests/test_model_router.py
--------------------------------
Unit tests for services/model_router.py.

Tests cover:
- mock provider used when ENABLE_REAL_LLM=false (default)
- mock provider used even if LLM_ROLE_CONFIG_JSON specifies a real provider when
  ENABLE_REAL_LLM=false — wait: the router uses the config as-is; the mock fallback
  is applied by get_llm_role_config when the role is missing.  When the role IS in
  config with provider=mock, it stays mock.  When it's missing, it falls back to mock.
- LlmConfigurationError raised when ENABLE_REAL_LLM=true and role missing
- dict messages are coerced to LlmMessage
- stream works with mock provider
- unknown provider raises LlmConfigurationError

No real network calls in any test.
"""

from __future__ import annotations

import json

import pytest

import config as cfg_module
from schemas.llm import LlmMessage, LlmResponse, LlmStreamChunk
from services import model_router
from services.llm_providers.errors import LlmConfigurationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings():
    """Reset the Settings singleton so monkeypatched env vars take effect."""
    cfg_module._settings = None


# ---------------------------------------------------------------------------
# generate() — mock path
# ---------------------------------------------------------------------------


class TestModelRouterGenerate:
    def test_uses_mock_when_real_llm_disabled_role_missing(self, monkeypatch):
        """Default: ENABLE_REAL_LLM=false → missing role falls back to mock."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = model_router.generate(
            "classifier", [LlmMessage(role="user", content="hello")]
        )

        assert isinstance(result, LlmResponse)
        assert result.provider == "mock"
        assert result.model_label == "local-mock"
        _reset_settings()

    def test_uses_mock_when_role_configured_as_mock(self, monkeypatch):
        """Explicit mock config is honoured."""
        role_cfg = {"solver": {"provider": "mock", "model_label": "explicit-mock"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        result = model_router.generate(
            "solver", [LlmMessage(role="user", content="solve this")]
        )

        assert result.provider == "mock"
        assert result.model_label == "explicit-mock"
        _reset_settings()

    def test_content_echoes_user_message(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = model_router.generate(
            "test-role", [LlmMessage(role="user", content="test content here")]
        )

        assert "test content here" in result.content
        _reset_settings()

    def test_dict_messages_coerced(self, monkeypatch):
        """Plain dicts are accepted and coerced to LlmMessage."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = model_router.generate(
            "test-role", [{"role": "user", "content": "dict message"}]
        )

        assert isinstance(result, LlmResponse)
        assert "dict message" in result.content
        _reset_settings()

    def test_response_role_matches_request(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = model_router.generate(
            "my-role", [LlmMessage(role="user", content="hi")]
        )

        assert result.role == "my-role"
        _reset_settings()


# ---------------------------------------------------------------------------
# generate() — error paths
# ---------------------------------------------------------------------------


class TestModelRouterGenerateErrors:
    def test_raises_config_error_when_real_llm_true_and_role_missing(self, monkeypatch):
        """ENABLE_REAL_LLM=true + no role config → hard error."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        with pytest.raises(LlmConfigurationError, match="ENABLE_REAL_LLM=true"):
            model_router.generate(
                "missing-role", [LlmMessage(role="user", content="hi")]
            )
        _reset_settings()

    def test_raises_config_error_for_unknown_provider(self, monkeypatch):
        """Unknown provider name in role config raises LlmConfigurationError."""
        # Monkeypatch get_llm_role_config to return a config with an unknown provider name.
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        from schemas.llm import LlmRoleConfig

        # Monkeypatch get_llm_role_config to return a config with invalid provider
        def _bad_config(role, settings=None):  # noqa: ARG001
            return LlmRoleConfig.model_construct(
                provider="bedrock",  # type: ignore[arg-type]
                model_label="test",
                deployment=None,
                model=None,
                temperature=0.2,
                max_tokens=1200,
                supports_streaming=False,
            )

        monkeypatch.setattr(cfg_module, "get_llm_role_config", _bad_config)

        with pytest.raises(LlmConfigurationError, match="Unknown provider"):
            model_router.generate("solver", [LlmMessage(role="user", content="hi")])

        monkeypatch.undo()
        _reset_settings()

    def test_malformed_role_config_json_raises(self, monkeypatch):
        """Non-JSON value in LLM_ROLE_CONFIG_JSON → LlmConfigurationError."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "NOT_VALID_JSON")
        _reset_settings()

        with pytest.raises(LlmConfigurationError, match="not valid JSON"):
            model_router.generate("any", [LlmMessage(role="user", content="hi")])
        _reset_settings()


# ---------------------------------------------------------------------------
# stream() — mock path
# ---------------------------------------------------------------------------


class TestModelRouterStream:
    def test_stream_yields_chunks(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        chunks = list(
            model_router.stream("test-role", [LlmMessage(role="user", content="stream test")])
        )

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, LlmStreamChunk)
        _reset_settings()

    def test_stream_last_chunk_is_final(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        chunks = list(
            model_router.stream("test-role", [LlmMessage(role="user", content="a b c")])
        )

        assert chunks[-1].is_final is True
        _reset_settings()

    def test_stream_dict_messages_coerced(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        chunks = list(
            model_router.stream("test-role", [{"role": "user", "content": "dict stream"}])
        )

        assert len(chunks) > 0
        _reset_settings()

    def test_stream_raises_config_error_when_real_llm_true_and_role_missing(
        self, monkeypatch
    ):
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        with pytest.raises(LlmConfigurationError):
            list(model_router.stream("missing", [LlmMessage(role="user", content="hi")]))
        _reset_settings()


# ---------------------------------------------------------------------------
# get_llm_role_config — config parsing
# ---------------------------------------------------------------------------


class TestGetLlmRoleConfig:
    def test_role_config_json_parsed_into_llm_role_config(self, monkeypatch):
        """LLM_ROLE_CONFIG_JSON is parsed and validated correctly."""
        from config import get_llm_role_config
        from schemas.llm import LlmRoleConfig

        role_cfg = {
            "classifier": {
                "provider": "azure_openai",
                "model_label": "gpt-4o-mini",
                "deployment": "dep-gpt4omini",
                "temperature": 0.1,
                "max_tokens": 500,
            }
        }
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        result = get_llm_role_config("classifier")

        assert isinstance(result, LlmRoleConfig)
        assert result.provider == "azure_openai"
        assert result.model_label == "gpt-4o-mini"
        assert result.deployment == "dep-gpt4omini"
        assert result.temperature == 0.1
        assert result.max_tokens == 500
        _reset_settings()

    def test_missing_role_returns_mock_default_when_real_llm_false(self, monkeypatch):
        from config import get_llm_role_config

        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = get_llm_role_config("non-existent-role")

        assert result.provider == "mock"
        assert result.model_label == "local-mock"
        assert result.supports_streaming is True
        _reset_settings()

    def test_missing_role_raises_when_real_llm_true(self, monkeypatch):
        from config import get_llm_role_config

        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        with pytest.raises(LlmConfigurationError):
            get_llm_role_config("missing-role")
        _reset_settings()
