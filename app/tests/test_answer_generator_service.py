"""
app/tests/test_answer_generator_service.py
--------------------------------------------
Unit tests for services/answer_generator_service.py.

Tests cover:
- mock path returns AnswerOutput with answer_source="mock"
- LLM path returns AnswerOutput with answer_source="llm"
- exception / empty / whitespace response → fallback AnswerOutput (source="fallback")
- model answer > 8000 chars is truncated to 8000 and is_truncated=True
- malformed LLM_ROLE_CONFIG_JSON → mock AnswerOutput (source="mock"), not crash
- role not configured → mock AnswerOutput (source="mock")
- classification context present in messages sent to model_router
- _build_answer_messages structure (roles, query, intent, subject, topic)
- prompt_loader called rather than direct file I/O
- no real network/model/AWS calls in any test

Settings singleton is reset between tests to honour monkeypatched env vars.
"""

from __future__ import annotations

import json

import config as cfg_module
from schemas.doubt_solver import AnswerOutput, QueryClassification
from services.answer_generator_service import (
    _GENERATOR_ROLE,
    _MAX_ANSWER_LEN,
    _build_answer_messages,
    _mock_answer,
    generate_answer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings():
    """Reset the Settings singleton so monkeypatched env vars take effect."""
    cfg_module._settings = None


def _make_classification(
    intent: str = "solve_question",
    subject: str = "math",
    confidence: float = 0.75,
    topic: str | None = "percentage",
) -> QueryClassification:
    return QueryClassification(
        intent=intent,  # type: ignore[arg-type]
        subject=subject,
        topic=topic,
        confidence=confidence,
    )


def _make_llm_response(content: str = "Here is the answer from the model."):
    from schemas.llm import LlmResponse

    return LlmResponse(
        role=_GENERATOR_ROLE,
        provider="mock",
        model_label="test-generator",
        content=content,
        finish_reason="stop",
    )


# ---------------------------------------------------------------------------
# Mock path (ENABLE_REAL_LLM=false) — returns AnswerOutput(source="mock")
# ---------------------------------------------------------------------------


class TestMockPath:
    def test_returns_answer_output_when_real_llm_false(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = generate_answer("What is 20% of 500?", _make_classification())

        assert isinstance(result, AnswerOutput)
        assert len(result.content) > 0
        _reset_settings()

    def test_mock_path_source_is_mock(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        _reset_settings()

        result = generate_answer("Explain ratio", _make_classification(intent="explain_concept"))

        assert result.answer_source == "mock"
        _reset_settings()

    def test_mock_path_is_not_truncated(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        _reset_settings()

        result = generate_answer("anything", _make_classification())

        assert result.is_truncated is False
        _reset_settings()

    def test_default_is_mock(self, monkeypatch):
        """No ENABLE_REAL_LLM set -> default false -> mock path."""
        monkeypatch.delenv("ENABLE_REAL_LLM", raising=False)
        _reset_settings()

        result = generate_answer("anything", _make_classification())

        assert isinstance(result, AnswerOutput)
        assert result.answer_source == "mock"
        _reset_settings()

    def test_mock_path_not_used_when_real_llm_true(self, monkeypatch):
        """Verify model_router.generate IS called when ENABLE_REAL_LLM=true."""
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        call_count = {"n": 0}

        def _fake_generate(role, messages):
            call_count["n"] += 1
            return _make_llm_response("LLM answer")

        monkeypatch.setattr(model_router_module, "generate", _fake_generate)

        generate_answer("any query", _make_classification())

        assert call_count["n"] == 1
        _reset_settings()


# ---------------------------------------------------------------------------
# Direct _mock_answer tests — returns AnswerOutput
# ---------------------------------------------------------------------------


class TestMockAnswer:
    def test_returns_answer_output(self):
        result = _mock_answer("Solve for x in 2x = 10", _make_classification())
        assert isinstance(result, AnswerOutput)

    def test_source_is_mock(self):
        result = _mock_answer("Solve for x in 2x = 10", _make_classification())
        assert result.answer_source == "mock"

    def test_solve_question_contains_steps(self):
        result = _mock_answer("Solve for x in 2x = 10", _make_classification())
        assert "Step 1" in result.content
        assert "Step 2" in result.content

    def test_explain_concept_non_empty(self):
        result = _mock_answer(
            "Explain osmosis", _make_classification(intent="explain_concept")
        )
        assert len(result.content) > 0

    def test_explain_option_non_empty(self):
        result = _mock_answer(
            "Why is option B correct?",
            _make_classification(intent="explain_option"),
        )
        assert len(result.content) > 0

    def test_unknown_intent_returns_fallback_text(self):
        result = _mock_answer("???", _make_classification(intent="unknown"))
        assert "rephrase" in result.content.lower() or len(result.content) > 0

    def test_general_doubt_non_empty(self):
        result = _mock_answer(
            "I am confused", _make_classification(intent="general_doubt")
        )
        assert len(result.content) > 0

    def test_is_not_truncated(self):
        result = _mock_answer("What is 10 + 10?", _make_classification())
        assert result.is_truncated is False


# ---------------------------------------------------------------------------
# LLM path — valid response; returns AnswerOutput(source="llm")
# ---------------------------------------------------------------------------


class TestLlmPath:
    def _setup_llm_env(self, monkeypatch, response_content: str = "LLM answer text."):
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        monkeypatch.setattr(
            model_router_module,
            "generate",
            lambda role, msgs: _make_llm_response(response_content),
        )

    def test_returns_answer_output(self, monkeypatch):
        self._setup_llm_env(monkeypatch, "Here is a detailed tutoring answer.")

        result = generate_answer("Calculate 20% of 500", _make_classification())

        assert isinstance(result, AnswerOutput)
        _reset_settings()

    def test_llm_source_is_llm(self, monkeypatch):
        self._setup_llm_env(monkeypatch, "Here is a detailed tutoring answer.")

        result = generate_answer("Calculate 20% of 500", _make_classification())

        assert result.answer_source == "llm"
        _reset_settings()

    def test_returns_llm_content(self, monkeypatch):
        self._setup_llm_env(monkeypatch, "Here is a detailed tutoring answer.")

        result = generate_answer("Calculate 20% of 500", _make_classification())

        assert result.content == "Here is a detailed tutoring answer."
        _reset_settings()

    def test_llm_path_strips_whitespace(self, monkeypatch):
        self._setup_llm_env(monkeypatch, "  Answer with surrounding whitespace.  ")

        result = generate_answer("anything", _make_classification())

        assert result.content == "Answer with surrounding whitespace."
        _reset_settings()

    def test_llm_is_not_truncated_for_short_answer(self, monkeypatch):
        self._setup_llm_env(monkeypatch, "Short answer.")

        result = generate_answer("anything", _make_classification())

        assert result.is_truncated is False
        _reset_settings()

    def test_classification_context_in_messages(self, monkeypatch):
        """Verify classification fields appear in the user message sent to model_router."""
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        captured: dict = {}

        def _capturing_generate(role, messages):
            captured["messages"] = messages
            return _make_llm_response("captured answer")

        monkeypatch.setattr(model_router_module, "generate", _capturing_generate)

        classification = _make_classification(
            intent="explain_concept", subject="science", confidence=0.8
        )
        generate_answer("Explain photosynthesis", classification)

        assert "messages" in captured
        user_msg = captured["messages"][1]
        user_content = user_msg.content if hasattr(user_msg, "content") else user_msg["content"]
        assert "explain_concept" in user_content
        assert "science" in user_content
        assert "0.80" in user_content
        _reset_settings()

    def test_role_passed_to_model_router(self, monkeypatch):
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        captured_role: list = []

        def _capturing_generate(role, messages):
            captured_role.append(role)
            return _make_llm_response("answer")

        monkeypatch.setattr(model_router_module, "generate", _capturing_generate)

        generate_answer("any query", _make_classification())

        assert captured_role[0] == _GENERATOR_ROLE
        _reset_settings()


# ---------------------------------------------------------------------------
# Answer truncation — model returns more than _MAX_ANSWER_LEN chars
# ---------------------------------------------------------------------------


class TestTruncation:
    def _setup_llm_env_with_content(self, monkeypatch, content: str):
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()
        monkeypatch.setattr(
            model_router_module,
            "generate",
            lambda role, msgs: _make_llm_response(content),
        )

    def test_too_long_answer_is_truncated_to_max_len(self, monkeypatch):
        long_content = "A" * (_MAX_ANSWER_LEN + 500)
        self._setup_llm_env_with_content(monkeypatch, long_content)

        result = generate_answer("any question", _make_classification())

        assert len(result.content) == _MAX_ANSWER_LEN
        _reset_settings()

    def test_too_long_answer_sets_is_truncated_true(self, monkeypatch):
        long_content = "B" * (_MAX_ANSWER_LEN + 1)
        self._setup_llm_env_with_content(monkeypatch, long_content)

        result = generate_answer("any question", _make_classification())

        assert result.is_truncated is True
        _reset_settings()

    def test_too_long_answer_source_is_llm(self, monkeypatch):
        """Truncation still yields answer_source=llm (not fallback)."""
        long_content = "C" * (_MAX_ANSWER_LEN + 1)
        self._setup_llm_env_with_content(monkeypatch, long_content)

        result = generate_answer("any question", _make_classification())

        assert result.answer_source == "llm"
        _reset_settings()

    def test_exact_max_length_not_truncated(self, monkeypatch):
        exact_content = "D" * _MAX_ANSWER_LEN
        self._setup_llm_env_with_content(monkeypatch, exact_content)

        result = generate_answer("any question", _make_classification())

        assert result.is_truncated is False
        assert len(result.content) == _MAX_ANSWER_LEN
        _reset_settings()


# ---------------------------------------------------------------------------
# Fallback paths — source="fallback"
# ---------------------------------------------------------------------------


class TestLlmFallbackPaths:
    def _setup_llm_env_with_fake(self, monkeypatch, fake_generate):
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()
        monkeypatch.setattr(model_router_module, "generate", fake_generate)

    def test_exception_returns_fallback_source(self, monkeypatch):
        def _failing(role, messages):
            raise RuntimeError("Simulated provider failure")

        self._setup_llm_env_with_fake(monkeypatch, _failing)

        result = generate_answer("Solve for x", _make_classification())

        assert result.answer_source == "fallback"
        _reset_settings()

    def test_exception_returns_non_empty_content(self, monkeypatch):
        def _failing(role, messages):
            raise RuntimeError("Simulated provider failure")

        self._setup_llm_env_with_fake(monkeypatch, _failing)

        result = generate_answer("Solve for x", _make_classification())

        assert len(result.content) > 0
        _reset_settings()

    def test_empty_content_returns_fallback_source(self, monkeypatch):
        self._setup_llm_env_with_fake(monkeypatch, lambda r, m: _make_llm_response(""))

        result = generate_answer("any question", _make_classification())

        assert result.answer_source == "fallback"
        _reset_settings()

    def test_whitespace_only_content_returns_fallback_source(self, monkeypatch):
        self._setup_llm_env_with_fake(
            monkeypatch, lambda r, m: _make_llm_response("   \n  ")
        )

        result = generate_answer("any question", _make_classification())

        assert result.answer_source == "fallback"
        _reset_settings()

    def test_malformed_config_json_returns_mock_source(self, monkeypatch):
        """Malformed LLM_ROLE_CONFIG_JSON -> mock path (not fallback, not crash)."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "NOT_VALID_JSON")
        _reset_settings()

        result = generate_answer("Explain osmosis", _make_classification(intent="explain_concept"))

        assert isinstance(result, AnswerOutput)
        assert result.answer_source == "mock"
        _reset_settings()

    def test_role_not_in_config_returns_mock_source(self, monkeypatch):
        """Role absent from config -> mock path (not fallback)."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = generate_answer("Solve 2+2", _make_classification())

        assert result.answer_source == "mock"
        _reset_settings()

    def test_fallback_is_not_truncated(self, monkeypatch):
        def _failing(role, messages):
            raise RuntimeError("fail")

        self._setup_llm_env_with_fake(monkeypatch, _failing)

        result = generate_answer("anything", _make_classification())

        assert result.is_truncated is False
        _reset_settings()


# ---------------------------------------------------------------------------
# _build_answer_messages structure
# ---------------------------------------------------------------------------


class TestBuildAnswerMessages:
    def test_returns_two_messages(self):
        msgs = _build_answer_messages("What is osmosis?", _make_classification())
        assert len(msgs) == 2

    def test_first_message_is_system(self):
        msgs = _build_answer_messages("anything", _make_classification())
        role = msgs[0].role if hasattr(msgs[0], "role") else msgs[0]["role"]
        assert role == "system"

    def test_second_message_is_user(self):
        msgs = _build_answer_messages("anything", _make_classification())
        role = msgs[1].role if hasattr(msgs[1], "role") else msgs[1]["role"]
        assert role == "user"

    def test_user_message_contains_query(self):
        query = "What is the formula for kinetic energy?"
        msgs = _build_answer_messages(query, _make_classification(subject="science"))
        content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert query in content

    def test_user_message_contains_intent(self):
        msgs = _build_answer_messages(
            "explain ratio",
            _make_classification(intent="explain_concept"),
        )
        content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert "explain_concept" in content

    def test_user_message_contains_subject(self):
        msgs = _build_answer_messages(
            "compute the ratio",
            _make_classification(subject="math"),
        )
        content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert "math" in content

    def test_user_message_contains_topic_when_present(self):
        msgs = _build_answer_messages(
            "any query",
            _make_classification(topic="percentage"),
        )
        content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert "percentage" in content

    def test_user_message_omits_topic_when_none(self):
        msgs = _build_answer_messages(
            "any query",
            _make_classification(topic=None),
        )
        content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert "Topic:" not in content

    def test_system_message_non_empty(self):
        msgs = _build_answer_messages("anything", _make_classification())
        content = msgs[0].content if hasattr(msgs[0], "content") else msgs[0]["content"]
        assert len(content) > 50  # prompt file should be non-trivial


# ---------------------------------------------------------------------------
# prompt_loader is used (not direct file I/O)
# ---------------------------------------------------------------------------


class TestPromptLoaderUsed:
    def test_build_messages_uses_prompt_loader(self, monkeypatch):
        """Verify _build_answer_messages calls prompt_loader, not direct Path.read_text."""
        import services.prompt_loader as loader_module

        call_count = {"n": 0}

        def _counting_load(name: str) -> str:
            call_count["n"] += 1
            return "System prompt content for testing."

        monkeypatch.setattr(loader_module, "load_prompt", _counting_load)

        _build_answer_messages("test query", _make_classification())

        assert call_count["n"] >= 1


# ---------------------------------------------------------------------------
# Part 9: context parameter
# ---------------------------------------------------------------------------


class TestContextParameter:
    """Tests for the optional context parameter added in Part 9."""

    def test_generate_answer_without_context_keeps_mock_behavior(self, monkeypatch):
        """Existing call without context still returns mock answer."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        _reset_settings()

        result = generate_answer("What is 5 + 5?", _make_classification())

        assert result.answer_source == "mock"
        _reset_settings()

    def test_generate_answer_with_context_none_keeps_mock_behavior(self, monkeypatch):
        """Passing context=None is identical to not passing context."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        _reset_settings()

        result = generate_answer("What is 5 + 5?", _make_classification(), context=None)

        assert result.answer_source == "mock"
        _reset_settings()

    def test_context_included_in_user_message_for_llm(self, monkeypatch):
        """When context is provided, it appears in the user message sent to LLM."""
        import services.model_router as model_router_module

        role_cfg = {_GENERATOR_ROLE: {"provider": "mock", "model_label": "test-gen"}}
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        captured: dict = {}

        def _capturing_generate(role, messages):
            captured["messages"] = messages
            return _make_llm_response("Answer with context.")

        monkeypatch.setattr(model_router_module, "generate", _capturing_generate)

        test_context = "Reference: Algebra is a branch of math."
        generate_answer("Explain algebra", _make_classification(), context=test_context)

        assert "messages" in captured
        user_content = captured["messages"][1].content
        assert test_context in user_content
        _reset_settings()

    def test_context_not_in_system_message(self, monkeypatch):
        """Context appears in user message only — not in system message."""
        msgs = _build_answer_messages(
            "Explain ratio",
            _make_classification(),
            context="Some reference context.",
        )
        system_content = msgs[0].content if hasattr(msgs[0], "content") else msgs[0]["content"]
        assert "Some reference context." not in system_content

    def test_context_in_user_message(self, monkeypatch):
        """Context string appears in user message when provided."""
        test_context = "Unique marker: XYZ reference text."
        msgs = _build_answer_messages(
            "What is ratio?",
            _make_classification(),
            context=test_context,
        )
        user_content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert test_context in user_content

    def test_no_context_does_not_add_context_section(self):
        """Without context, user message has no reference context section."""
        msgs = _build_answer_messages(
            "What is ratio?",
            _make_classification(),
            context=None,
        )
        user_content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        assert "Retrieved Reference Context" not in user_content

    def test_context_labeled_as_reference_not_instruction(self):
        """Context section must be labeled as reference/not-instruction."""
        msgs = _build_answer_messages(
            "What is ratio?",
            _make_classification(),
            context="Some context text.",
        )
        user_content = msgs[1].content if hasattr(msgs[1], "content") else msgs[1]["content"]
        # Should contain clear label that it's reference material, not instructions.
        assert "reference" in user_content.lower() or "not instructions" in user_content.lower()

    def test_empty_context_string_not_appended(self):
        """Empty context string behaves like no context (no section added)."""
        msgs_no_ctx = _build_answer_messages(
            "Explain osmosis", _make_classification(), context=None
        )
        msgs_empty_ctx = _build_answer_messages(
            "Explain osmosis", _make_classification(), context=""
        )
        content_no = (
            msgs_no_ctx[1].content
            if hasattr(msgs_no_ctx[1], "content")
            else msgs_no_ctx[1]["content"]
        )
        content_empty = (
            msgs_empty_ctx[1].content
            if hasattr(msgs_empty_ctx[1], "content")
            else msgs_empty_ctx[1]["content"]
        )
        # Both should produce identical user messages (empty string treated as no context).
        assert content_no == content_empty

