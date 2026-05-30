"""
app/tests/test_llm_schemas.py
------------------------------
Unit tests for schemas/llm.py.

Tests cover: field validation, allowed literals, constraints, role config parsing.
No network calls. No real LLM. No env var dependencies.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.llm import LlmMessage, LlmRequest, LlmResponse, LlmRoleConfig, LlmStreamChunk

# ---------------------------------------------------------------------------
# LlmMessage
# ---------------------------------------------------------------------------


class TestLlmMessage:
    def test_valid_system_message(self):
        msg = LlmMessage(role="system", content="You are a tutor.")
        assert msg.role == "system"
        assert msg.content == "You are a tutor."

    def test_valid_user_message(self):
        msg = LlmMessage(role="user", content="What is 2+2?")
        assert msg.role == "user"

    def test_valid_assistant_message(self):
        msg = LlmMessage(role="assistant", content="The answer is 4.")
        assert msg.role == "assistant"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            LlmMessage(role="unknown", content="hello")  # type: ignore[arg-type]

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            LlmMessage(role="user", content="")


# ---------------------------------------------------------------------------
# LlmRoleConfig
# ---------------------------------------------------------------------------


class TestLlmRoleConfig:
    def test_mock_provider_minimal(self):
        cfg = LlmRoleConfig(provider="mock", model_label="local-mock")
        assert cfg.provider == "mock"
        assert cfg.model_label == "local-mock"
        assert cfg.temperature == 0.2
        assert cfg.max_tokens == 1200
        assert cfg.supports_streaming is False
        assert cfg.deployment is None
        assert cfg.model is None

    def test_azure_provider_with_deployment(self):
        cfg = LlmRoleConfig(
            provider="azure_openai",
            model_label="gpt-4o-mini",
            deployment="my-gpt4o-deployment",
        )
        assert cfg.provider == "azure_openai"
        assert cfg.deployment == "my-gpt4o-deployment"

    def test_openai_provider_with_model(self):
        cfg = LlmRoleConfig(
            provider="openai",
            model_label="gpt-4o",
            model="gpt-4o",
        )
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"

    def test_invalid_provider_rejected(self):
        with pytest.raises(ValidationError):
            LlmRoleConfig(provider="bedrock", model_label="x")  # type: ignore[arg-type]

    def test_temperature_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            LlmRoleConfig(provider="mock", model_label="x", temperature=3.0)

    def test_max_tokens_zero_rejected(self):
        with pytest.raises(ValidationError):
            LlmRoleConfig(provider="mock", model_label="x", max_tokens=0)

    def test_supports_streaming_true(self):
        cfg = LlmRoleConfig(provider="mock", model_label="x", supports_streaming=True)
        assert cfg.supports_streaming is True

    def test_model_validate_from_dict(self):
        """Role config JSON dict round-trips correctly."""
        raw = {
            "provider": "openai",
            "model_label": "gpt-4o",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 800,
        }
        cfg = LlmRoleConfig.model_validate(raw)
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 800


# ---------------------------------------------------------------------------
# LlmRequest
# ---------------------------------------------------------------------------


class TestLlmRequest:
    def test_valid_request(self):
        req = LlmRequest(
            role="classifier",
            messages=[LlmMessage(role="user", content="hello")],
        )
        assert req.role == "classifier"
        assert len(req.messages) == 1

    def test_empty_messages_rejected(self):
        with pytest.raises(ValidationError):
            LlmRequest(role="classifier", messages=[])

    def test_temperature_override(self):
        req = LlmRequest(
            role="classifier",
            messages=[LlmMessage(role="user", content="hello")],
            temperature=0.7,
        )
        assert req.temperature == 0.7

    def test_max_tokens_override(self):
        req = LlmRequest(
            role="solver",
            messages=[LlmMessage(role="user", content="solve this")],
            max_tokens=500,
        )
        assert req.max_tokens == 500


# ---------------------------------------------------------------------------
# LlmResponse
# ---------------------------------------------------------------------------


class TestLlmResponse:
    def test_valid_response(self):
        resp = LlmResponse(
            role="classifier",
            provider="mock",
            model_label="local-mock",
            content="mocked content",
        )
        assert resp.content == "mocked content"
        assert resp.finish_reason is None

    def test_finish_reason_populated(self):
        resp = LlmResponse(
            role="classifier",
            provider="mock",
            model_label="local-mock",
            content="done",
            finish_reason="stop",
        )
        assert resp.finish_reason == "stop"


# ---------------------------------------------------------------------------
# LlmStreamChunk
# ---------------------------------------------------------------------------


class TestLlmStreamChunk:
    def test_non_final_chunk(self):
        chunk = LlmStreamChunk(
            role="solver",
            provider="mock",
            model_label="local-mock",
            content_delta="Hello ",
        )
        assert chunk.is_final is False
        assert chunk.content_delta == "Hello "

    def test_final_chunk(self):
        chunk = LlmStreamChunk(
            role="solver",
            provider="mock",
            model_label="local-mock",
            content_delta="world",
            is_final=True,
        )
        assert chunk.is_final is True
