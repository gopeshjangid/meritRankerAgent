"""
app/tests/test_schemas.py
--------------------------
Unit tests for the Pydantic request/response/state schemas.

These tests run without any network calls or AWS credentials.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.request import AgentRequest
from schemas.response import AgentResponse
from schemas.state import AgentState

# ---------------------------------------------------------------------------
# AgentRequest
# ---------------------------------------------------------------------------


class TestAgentRequest:
    def test_valid_minimal_request(self):
        """Default fields should be applied when omitted."""
        req = AgentRequest(message="hello")
        assert req.message == "hello"
        assert req.user_id == "local-user"
        assert req.mode == "demo"

    def test_valid_full_request(self):
        req = AgentRequest(message="test msg", user_id="user-42", mode="production")
        assert req.user_id == "user-42"
        assert req.mode == "production"

    def test_empty_message_fails(self):
        with pytest.raises(ValidationError):
            AgentRequest(message="")

    def test_message_too_long_fails(self):
        with pytest.raises(ValidationError):
            AgentRequest(message="x" * 5001)

    def test_whitespace_only_message_fails(self):
        """str_strip_whitespace=True means whitespace-only becomes '' → invalid."""
        with pytest.raises(ValidationError):
            AgentRequest(message="   ")

    def test_empty_user_id_fails(self):
        with pytest.raises(ValidationError):
            AgentRequest(message="hello", user_id="")

    def test_model_validate_from_dict(self):
        """model_validate is the Pydantic v2 way to build from a plain dict."""
        data = {"message": "hi", "user_id": "alice", "mode": "demo"}
        req = AgentRequest.model_validate(data)
        assert req.message == "hi"


# ---------------------------------------------------------------------------
# AgentResponse
# ---------------------------------------------------------------------------


class TestAgentResponse:
    def test_valid_success_response(self):
        resp = AgentResponse(
            success=True,
            answer="it works",
            request_id="req-001",
            mode="demo",
        )
        assert resp.success is True

    def test_model_dump_returns_dict(self):
        resp = AgentResponse(
            success=True,
            answer="hello",
            request_id="req-002",
            mode="demo",
        )
        data = resp.model_dump()
        assert isinstance(data, dict)
        assert data["success"] is True
        assert data["answer"] == "hello"
        assert data["request_id"] == "req-002"
        assert data["mode"] == "demo"

    def test_failure_response(self):
        resp = AgentResponse(
            success=False,
            answer="Internal error: boom",
            request_id="unknown",
            mode="demo",
        )
        assert resp.success is False
        assert "boom" in resp.answer


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------


class TestAgentState:
    def test_valid_state(self):
        req = AgentRequest(message="hello")
        state = AgentState(request=req, request_id="req-003")
        assert state.answer is None  # default

    def test_state_with_answer(self):
        req = AgentRequest(message="hello")
        state = AgentState(request=req, request_id="req-004", answer="world")
        assert state.answer == "world"
