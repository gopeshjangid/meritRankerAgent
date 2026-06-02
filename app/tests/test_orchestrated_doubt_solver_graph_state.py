"""
tests/test_orchestrated_doubt_solver_graph_state.py
------------------------------------------
Unit tests: OrchestratedDoubtSolverState shape and DoubtSolverClassification schema.

Verifies that the orchestrated graph state:
- Contains only the 5 required fields (request_id, query, classification,
  context_text, answer).
- Does NOT carry plan, response, sources, route_decision, prompt/messages, or
  raw provider response fields.
- Initialises with safe defaults.
- Accepts minimal query/request_id.

Also verifies DoubtSolverClassification has only the 4 required fields and that
defaults are correct.

No graph execution happens in this file — state shape and schema only.
"""

from __future__ import annotations

from graphs.doubt_solver_graph import OrchestratedDoubtSolverState
from schemas.doubt_solver import DoubtSolverClassification

# ===========================================================================
# OrchestratedDoubtSolverState shape tests
# ===========================================================================


class TestOrchestratedDoubtSolverStateShape:
    """Verify the TypedDict carries only the 5 declared fields."""

    def test_state_has_request_id_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert state["request_id"] == "test-id"

    def test_state_has_query_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "What is 2+2?",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert state["query"] == "What is 2+2?"

    def test_state_has_classification_field(self) -> None:
        clf = {
            "subject": "math",
            "intent": "solve",
            "difficulty": "default",
            "retrieval_required": False,
        }
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": clf,
            "context_text": "",
            "answer": None,
        }
        assert state["classification"] == clf

    def test_state_has_context_text_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "Some context.",
            "answer": None,
        }
        assert state["context_text"] == "Some context."

    def test_state_has_answer_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": "The answer is 4.",
        }
        assert state["answer"] == "The answer is 4."

    def test_state_classification_defaults_to_none(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert state["classification"] is None

    def test_state_answer_defaults_to_none(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert state["answer"] is None

    def test_state_context_text_defaults_to_empty_string(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert state["context_text"] == ""

    def test_state_has_exactly_five_keys(self) -> None:
        """V1 state must not carry extra legacy fields."""
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert set(state.keys()) == {
            "request_id",
            "query",
            "classification",
            "context_text",
            "answer",
        }

    def test_state_does_not_have_plan_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "plan" not in state

    def test_state_does_not_have_response_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "response" not in state

    def test_state_does_not_have_route_decision_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "route_decision" not in state

    def test_state_does_not_have_messages_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "messages" not in state

    def test_state_does_not_have_raw_provider_response_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "raw_provider_response" not in state

    def test_state_does_not_have_kb_results_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "kb_results" not in state

    def test_state_does_not_have_dynamodb_records_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "dynamodb_records" not in state

    def test_state_does_not_have_used_retrieval_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "used_retrieval" not in state

    def test_state_does_not_have_answer_source_field(self) -> None:
        state: OrchestratedDoubtSolverState = {
            "request_id": "test-id",
            "query": "test",
            "classification": None,
            "context_text": "",
            "answer": None,
        }
        assert "answer_source" not in state


# ===========================================================================
# DoubtSolverClassification schema tests
# ===========================================================================


class TestDoubtSolverClassification:
    """Verify DoubtSolverClassification has correct fields and defaults."""

    def test_default_subject_is_general(self) -> None:
        clf = DoubtSolverClassification()
        assert clf.subject == "general"

    def test_default_intent_is_explain(self) -> None:
        clf = DoubtSolverClassification()
        assert clf.intent == "explain"

    def test_default_difficulty_is_default(self) -> None:
        clf = DoubtSolverClassification()
        assert clf.difficulty == "default"

    def test_default_retrieval_required_is_false(self) -> None:
        clf = DoubtSolverClassification()
        assert clf.retrieval_required is False

    def test_accepts_math_subject(self) -> None:
        clf = DoubtSolverClassification(subject="math", intent="solve", difficulty="advanced")
        assert clf.subject == "math"
        assert clf.intent == "solve"
        assert clf.difficulty == "advanced"

    def test_retrieval_required_can_be_true(self) -> None:
        clf = DoubtSolverClassification(retrieval_required=True)
        assert clf.retrieval_required is True

    def test_model_dump_includes_core_and_optional_hint_fields(self) -> None:
        clf = DoubtSolverClassification()
        dumped = clf.model_dump()
        assert {"subject", "intent", "difficulty", "retrieval_required"}.issubset(
            set(dumped.keys())
        )
        assert "topic" in dumped
        assert "retrieval_tags" in dumped

    def test_no_confidence_field(self) -> None:
        clf = DoubtSolverClassification()
        dumped = clf.model_dump()
        assert "confidence" not in dumped

    def test_topic_field_optional(self) -> None:
        clf = DoubtSolverClassification(topic="Age Problem")
        dumped = clf.model_dump()
        assert dumped["topic"] == "Age Problem"

    def test_no_response_style_field(self) -> None:
        clf = DoubtSolverClassification()
        dumped = clf.model_dump()
        assert "response_style" not in dumped

    def test_no_classification_source_field(self) -> None:
        clf = DoubtSolverClassification()
        dumped = clf.model_dump()
        assert "classification_source" not in dumped

    def test_no_retrieval_need_field(self) -> None:
        """V1 uses retrieval_required bool, not the legacy retrieval_need string."""
        clf = DoubtSolverClassification()
        dumped = clf.model_dump()
        assert "retrieval_need" not in dumped
