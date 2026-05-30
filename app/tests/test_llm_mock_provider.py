"""
app/tests/test_llm_mock_provider.py
-------------------------------------
Unit tests for services/llm_providers/mock_provider.py.

Tests cover: generate output, stream chunks, word splitting, empty content.
No network calls. No env var dependencies.
"""

from __future__ import annotations

import pytest

from schemas.llm import LlmMessage, LlmRequest, LlmRoleConfig
from services.llm_providers.mock_provider import MockProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> LlmRoleConfig:
    return LlmRoleConfig(
        provider="mock",
        model_label="test-mock",
        supports_streaming=True,
    )


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


def _make_request(content: str, role: str = "test-role") -> LlmRequest:
    return LlmRequest(
        role=role,
        messages=[LlmMessage(role="user", content=content)],
    )


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


class TestMockProviderGenerate:
    def test_echoes_last_user_message(self, provider, mock_config):
        req = _make_request("What is photosynthesis?")
        resp = provider.generate(req, mock_config)
        assert "What is photosynthesis?" in resp.content

    def test_provider_is_mock(self, provider, mock_config):
        req = _make_request("hello")
        resp = provider.generate(req, mock_config)
        assert resp.provider == "mock"

    def test_model_label_matches_config(self, provider, mock_config):
        req = _make_request("hello")
        resp = provider.generate(req, mock_config)
        assert resp.model_label == "test-mock"

    def test_role_matches_request(self, provider, mock_config):
        req = _make_request("hello", role="classifier")
        resp = provider.generate(req, mock_config)
        assert resp.role == "classifier"

    def test_finish_reason_is_stop(self, provider, mock_config):
        req = _make_request("test")
        resp = provider.generate(req, mock_config)
        assert resp.finish_reason == "stop"

    def test_uses_last_user_message_when_multiple(self, provider, mock_config):
        req = LlmRequest(
            role="solver",
            messages=[
                LlmMessage(role="system", content="You are a tutor."),
                LlmMessage(role="user", content="First question"),
                LlmMessage(role="assistant", content="First answer"),
                LlmMessage(role="user", content="Second question"),
            ],
        )
        resp = provider.generate(req, mock_config)
        assert "Second question" in resp.content
        assert "First question" not in resp.content

    def test_content_prefix(self, provider, mock_config):
        req = _make_request("hello world")
        resp = provider.generate(req, mock_config)
        assert resp.content.startswith("[mock] echo:")

    def test_content_is_string(self, provider, mock_config):
        req = _make_request("anything")
        resp = provider.generate(req, mock_config)
        assert isinstance(resp.content, str)


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------


class TestMockProviderStream:
    def test_yields_chunks(self, provider, mock_config):
        req = _make_request("explain gravity")
        chunks = list(provider.stream(req, mock_config))
        assert len(chunks) > 0

    def test_last_chunk_is_final(self, provider, mock_config):
        req = _make_request("explain gravity")
        chunks = list(provider.stream(req, mock_config))
        assert chunks[-1].is_final is True

    def test_non_final_chunks_not_final(self, provider, mock_config):
        req = _make_request("explain gravity here")
        chunks = list(provider.stream(req, mock_config))
        for chunk in chunks[:-1]:
            assert chunk.is_final is False

    def test_reassembled_content_matches_generate(self, provider, mock_config):
        req = _make_request("test message")
        expected = provider.generate(req, mock_config).content
        chunks = list(provider.stream(req, mock_config))
        reassembled = "".join(c.content_delta for c in chunks)
        assert reassembled == expected

    def test_stream_provider_field(self, provider, mock_config):
        req = _make_request("hello")
        chunks = list(provider.stream(req, mock_config))
        for chunk in chunks:
            assert chunk.provider == "mock"

    def test_stream_model_label_field(self, provider, mock_config):
        req = _make_request("hello")
        chunks = list(provider.stream(req, mock_config))
        for chunk in chunks:
            assert chunk.model_label == "test-mock"

    def test_stream_role_field(self, provider, mock_config):
        req = _make_request("hello", role="my-role")
        chunks = list(provider.stream(req, mock_config))
        for chunk in chunks:
            assert chunk.role == "my-role"
