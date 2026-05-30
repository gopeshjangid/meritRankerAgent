"""
app/tests/test_query_classifier_service.py
--------------------------------------------
Unit tests for services/query_classifier_service.py.

Tests cover:
- deterministic path when ENABLE_REAL_LLM=false
- LLM path with monkeypatched model_router (valid JSON response)
- malformed JSON → fallback
- invalid enum value in JSON → fallback
- model_router raises exception → fallback
- classification_source is set correctly for all paths
- deterministic path when ENABLE_REAL_LLM=true but role not in config
- no real network calls in any test

Settings singleton is reset between tests to honour monkeypatched env vars.
"""

from __future__ import annotations

import json

import config as cfg_module
from schemas.doubt_solver import QueryClassification
from services.query_classifier_service import (
    _CLASSIFIER_ROLE,
    _classify_deterministic,
    classify_query,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_settings():
    """Reset the Settings singleton so monkeypatched env vars take effect."""
    cfg_module._settings = None


def _make_valid_llm_response_content(
    intent: str = "solve_question",
    subject: str = "math",
    confidence: float = 0.9,
) -> str:
    """Return a JSON string that passes QueryClassification validation."""
    return json.dumps(
        {
            "intent": intent,
            "subject": subject,
            "topic": "percentage",
            "response_style": "step_by_step",
            "confidence": confidence,
            "retrieval_need": "none",
            "reasoning_summary": "Query is a calculation task.",
        }
    )


# ---------------------------------------------------------------------------
# Deterministic path (ENABLE_REAL_LLM=false)
# ---------------------------------------------------------------------------


class TestDeterministicPath:
    def test_returns_result_when_real_llm_false(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = classify_query("What is 20% of 500?")

        assert isinstance(result, QueryClassification)
        assert result.classification_source == "deterministic"
        _reset_settings()

    def test_intent_detected_correctly(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = classify_query("Calculate the percentage gain")

        assert result.intent == "solve_question"
        assert result.classification_source == "deterministic"
        _reset_settings()

    def test_general_doubt_fallback_intent(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REAL_LLM", "false")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = classify_query("xyzzy random gibberish")

        assert result.intent == "general_doubt"
        assert result.confidence == 0.55
        assert result.classification_source == "deterministic"
        _reset_settings()

    def test_deterministic_is_default_when_no_env(self, monkeypatch):
        """Default (no ENABLE_REAL_LLM set) should use deterministic."""
        monkeypatch.delenv("ENABLE_REAL_LLM", raising=False)
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")
        _reset_settings()

        result = classify_query("Explain the concept of ratio")

        assert result.classification_source == "deterministic"
        _reset_settings()


# ---------------------------------------------------------------------------
# Direct _classify_deterministic tests (no env dependency)
# ---------------------------------------------------------------------------


class TestClassifyDeterministic:
    def test_solve_question_intent(self):
        result = _classify_deterministic("Solve for x in 2x + 5 = 13")
        assert result.intent == "solve_question"
        assert result.confidence == 0.75

    def test_explain_concept_intent(self):
        result = _classify_deterministic("Explain the concept of osmosis")
        assert result.intent == "explain_concept"

    def test_explain_option_intent(self):
        result = _classify_deterministic("Which choice is correct here?")
        assert result.intent == "explain_option"

    def test_math_subject(self):
        result = _classify_deterministic("Find the profit percentage here")
        assert result.subject == "math"

    def test_classification_source_is_deterministic(self):
        result = _classify_deterministic("any query")
        assert result.classification_source == "deterministic"

    def test_response_style_step_by_step_for_solve(self):
        result = _classify_deterministic("Solve this equation")
        assert result.response_style == "step_by_step"

    def test_response_style_short_answer_keyword(self):
        result = _classify_deterministic("Give a short answer: what is osmosis?")
        assert result.response_style == "short_answer"

    def test_response_style_simple_explanation_keyword(self):
        result = _classify_deterministic("Explain in simple terms what ratio means")
        assert result.response_style == "simple_explanation"


# ---------------------------------------------------------------------------
# LLM path — valid response (monkeypatched)
# ---------------------------------------------------------------------------


class TestLlmPath:
    def _setup_llm_env(self, monkeypatch, intent: str = "solve_question"):
        """Configure env for LLM path and monkeypatch model_router.generate."""
        import services.model_router as model_router_module

        role_cfg = {
            _CLASSIFIER_ROLE: {
                "provider": "mock",
                "model_label": "test-classifier",
            }
        }
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        from schemas.llm import LlmResponse

        def _fake_generate(role, messages):
            return LlmResponse(
                role=role,
                provider="mock",
                model_label="test-classifier",
                content=_make_valid_llm_response_content(intent=intent),
                finish_reason="stop",
            )

        monkeypatch.setattr(model_router_module, "generate", _fake_generate)

    def test_llm_path_returns_classification(self, monkeypatch):
        self._setup_llm_env(monkeypatch)

        result = classify_query("Calculate profit on selling price")

        assert isinstance(result, QueryClassification)
        assert result.classification_source == "llm"
        _reset_settings()

    def test_llm_path_intent_from_model(self, monkeypatch):
        self._setup_llm_env(monkeypatch, intent="explain_concept")

        result = classify_query("anything")

        assert result.intent == "explain_concept"
        assert result.classification_source == "llm"
        _reset_settings()

    def test_llm_path_high_confidence(self, monkeypatch):
        self._setup_llm_env(monkeypatch)

        result = classify_query("anything")

        assert result.confidence == 0.9
        assert result.classification_source == "llm"
        _reset_settings()

    def test_llm_path_retrieval_need_populated(self, monkeypatch):
        self._setup_llm_env(monkeypatch)

        result = classify_query("anything")

        assert result.retrieval_need == "none"
        _reset_settings()

    def test_llm_path_reasoning_summary_populated(self, monkeypatch):
        self._setup_llm_env(monkeypatch)

        result = classify_query("anything")

        assert result.reasoning_summary == "Query is a calculation task."
        _reset_settings()


# ---------------------------------------------------------------------------
# Fallback paths (malformed/invalid LLM output, errors)
# ---------------------------------------------------------------------------


class TestLlmFallbackPaths:
    def _setup_llm_env_with_fake(self, monkeypatch, response_content: str):
        import services.model_router as model_router_module

        role_cfg = {
            _CLASSIFIER_ROLE: {
                "provider": "mock",
                "model_label": "test-classifier",
            }
        }
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        from schemas.llm import LlmResponse

        def _fake_generate(role, messages):
            return LlmResponse(
                role=role,
                provider="mock",
                model_label="test-classifier",
                content=response_content,
                finish_reason="stop",
            )

        monkeypatch.setattr(model_router_module, "generate", _fake_generate)

    def test_malformed_json_falls_back(self, monkeypatch):
        """Non-JSON model output → classification_source=fallback."""
        self._setup_llm_env_with_fake(monkeypatch, "NOT VALID JSON AT ALL")

        result = classify_query("Solve for x")

        assert result.classification_source == "fallback"
        _reset_settings()

    def test_malformed_json_confidence_capped(self, monkeypatch):
        """Fallback confidence must not exceed 0.55."""
        self._setup_llm_env_with_fake(monkeypatch, "NOT JSON")

        result = classify_query("Solve for x")

        assert result.confidence <= 0.55
        _reset_settings()

    def test_invalid_enum_intent_falls_back(self, monkeypatch):
        """Invalid intent value in JSON → validation error → fallback."""
        bad_json = json.dumps(
            {
                "intent": "do_homework",  # not an allowed value
                "subject": "math",
                "topic": None,
                "response_style": "step_by_step",
                "confidence": 0.9,
                "retrieval_need": "none",
                "reasoning_summary": None,
            }
        )
        self._setup_llm_env_with_fake(monkeypatch, bad_json)

        result = classify_query("anything")

        assert result.classification_source == "fallback"
        _reset_settings()

    def test_invalid_confidence_range_falls_back(self, monkeypatch):
        """Out-of-range confidence → validation error → fallback."""
        bad_json = json.dumps(
            {
                "intent": "solve_question",
                "subject": "math",
                "topic": None,
                "response_style": "step_by_step",
                "confidence": 1.5,  # > 1.0
                "retrieval_need": "none",
                "reasoning_summary": None,
            }
        )
        self._setup_llm_env_with_fake(monkeypatch, bad_json)

        result = classify_query("anything")

        assert result.classification_source == "fallback"
        _reset_settings()

    def test_model_router_exception_falls_back(self, monkeypatch):
        """model_router.generate raising an exception → fallback."""
        import services.model_router as model_router_module

        role_cfg = {
            _CLASSIFIER_ROLE: {
                "provider": "mock",
                "model_label": "test-classifier",
            }
        }
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", json.dumps(role_cfg))
        _reset_settings()

        def _failing_generate(role, messages):
            raise RuntimeError("Simulated provider failure")

        monkeypatch.setattr(model_router_module, "generate", _failing_generate)

        result = classify_query("Explain photosynthesis")

        assert result.classification_source == "fallback"
        _reset_settings()

    def test_fallback_intent_is_sensible(self, monkeypatch):
        """Fallback still produces a sensible intent from deterministic path."""
        self._setup_llm_env_with_fake(monkeypatch, "BAD JSON")

        result = classify_query("Calculate the profit here")

        # Deterministic path would return solve_question for "calculate"
        assert result.intent == "solve_question"
        assert result.classification_source == "fallback"
        _reset_settings()


# ---------------------------------------------------------------------------
# Role not configured when ENABLE_REAL_LLM=true → deterministic (not error)
# ---------------------------------------------------------------------------


class TestRoleNotConfigured:
    def test_uses_deterministic_when_role_missing(self, monkeypatch):
        """ENABLE_REAL_LLM=true but role not in config → deterministic, not error."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "{}")  # no classifier role
        _reset_settings()

        result = classify_query("Explain the concept of osmosis")

        assert isinstance(result, QueryClassification)
        assert result.classification_source == "deterministic"
        _reset_settings()

    def test_malformed_role_config_json_uses_fallback(self, monkeypatch):
        """Malformed LLM_ROLE_CONFIG_JSON with ENABLE_REAL_LLM=true → fallback, not silent."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "NOT_JSON")
        _reset_settings()

        result = classify_query("Explain photosynthesis")

        assert result.classification_source == "fallback"
        assert result.confidence <= 0.55
        _reset_settings()

    def test_malformed_role_config_json_fallback_still_classifies(self, monkeypatch):
        """Fallback from malformed config still returns a sensible classification."""
        monkeypatch.setenv("ENABLE_REAL_LLM", "true")
        monkeypatch.setenv("LLM_ROLE_CONFIG_JSON", "NOT_JSON")
        _reset_settings()

        result = classify_query("Solve for x in 2x = 10")

        assert result.intent == "solve_question"
        assert result.classification_source == "fallback"
        assert result.confidence <= 0.55
        _reset_settings()
