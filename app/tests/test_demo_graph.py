"""
app/tests/test_demo_graph.py
-----------------------------
Integration tests for the LangGraph demo workflow.

Tests verify end-to-end graph behaviour without any network or LLM calls.
"""

from __future__ import annotations

import uuid

from graphs.demo_graph import build_demo_graph


class TestDemoGraph:
    def test_build_returns_compiled_graph(self):
        """build_demo_graph() must return a compiled graph, not a builder."""
        graph = build_demo_graph()
        # Compiled LangGraph graphs expose an .invoke() method.
        assert callable(getattr(graph, "invoke", None)), (
            "Expected compiled graph with .invoke() method"
        )

    def test_graph_produces_answer(self):
        """The graph should populate 'answer' in the returned state."""
        graph = build_demo_graph()
        request_id = str(uuid.uuid4())
        result = graph.invoke(
            {
                "request_id": request_id,
                "message": "test local setup",
                "user_id": "local-user",
                "mode": "demo",
                "answer": None,
            }
        )
        assert result.get("answer"), "answer should not be empty"

    def test_answer_contains_input_message(self):
        """Mock service must echo the original message back."""
        graph = build_demo_graph()
        message = "hello from pytest"
        result = graph.invoke(
            {
                "request_id": "test-001",
                "message": message,
                "user_id": "test-user",
                "mode": "demo",
                "answer": None,
            }
        )
        assert message in result["answer"], (
            f"Expected message '{message}' to appear in answer: {result['answer']!r}"
        )

    def test_request_id_is_preserved(self):
        """The graph must not mutate or lose the request_id."""
        graph = build_demo_graph()
        request_id = str(uuid.uuid4())
        result = graph.invoke(
            {
                "request_id": request_id,
                "message": "check request id",
                "user_id": "local-user",
                "mode": "demo",
                "answer": None,
            }
        )
        assert result["request_id"] == request_id, (
            "request_id must be preserved through the graph unchanged"
        )

    def test_graph_is_reusable(self):
        """A compiled graph should handle multiple sequential invocations."""
        graph = build_demo_graph()
        for i in range(3):
            result = graph.invoke(
                {
                    "request_id": f"loop-{i}",
                    "message": f"message {i}",
                    "user_id": "local-user",
                    "mode": "demo",
                    "answer": None,
                }
            )
            assert f"message {i}" in result["answer"]
