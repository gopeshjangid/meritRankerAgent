"""
tests/test_orchestrated_streaming.py
--------------------------------------
Student-friendly orchestrated doubt solver streaming tests.
"""

from __future__ import annotations

import types

import pytest

from graphs.doubt_solver_graph import OrchestratedDoubtSolverState
from schemas.doubt_solver import DoubtSolverStreamEvent
from services.doubt_solver.answer_generation_adapter import AnswerGenerationAdapter
from services.doubt_solver.stream_labels import get_stream_label
from services.doubt_solver.streaming_doubt_solver_service import (
    StreamDoubtSolverInput,
    stream_doubt_solver,
)
from services.llm.orchestration.orchestrator import create_mock_orchestrator_for_tests

_REQUEST_ID = "test-req-stream-001"

_FORBIDDEN_CONTENT_SUBSTRINGS = {
    "prompt",
    "api_key",
    "secret",
    "credential",
    "authorization",
    "context_text",
    "raw_response",
    "Traceback",
}


def _make_adapter(
    content: str = "Let the cost price be ₹100. Marked price = ₹140.",
    *,
    raise_on_execute: Exception | None = None,
) -> AnswerGenerationAdapter:
    orchestrator, _ = create_mock_orchestrator_for_tests(
        content=content,
        raise_on_execute=raise_on_execute,
    )
    return AnswerGenerationAdapter(orchestrator=orchestrator)


def _collect(
    adapter: AnswerGenerationAdapter,
    *,
    query: str = "A profit question",
) -> list[DoubtSolverStreamEvent]:
    return list(
        stream_doubt_solver(
            StreamDoubtSolverInput(request_id=_REQUEST_ID, query=query),
            adapter=adapter,
        )
    )


class TestStreamEventSchema:
    def test_status_validates(self) -> None:
        event = DoubtSolverStreamEvent(
            type="status",
            request_id=_REQUEST_ID,
            stage="understanding",
            label="Understanding...",
        )
        assert event.type == "status"

    def test_sse_framing_from_model_dump(self) -> None:
        import json

        event = DoubtSolverStreamEvent(
            type="status",
            request_id=_REQUEST_ID,
            stage="understanding",
            label="Understanding...",
        )
        framed = f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
        assert framed.startswith("data: {")
        assert framed.endswith("\n\n")
        payload = json.loads(framed.removeprefix("data: ").strip())
        assert payload["type"] == "status"
        assert payload["request_id"] == _REQUEST_ID

    def test_chunk_validates(self) -> None:
        event = DoubtSolverStreamEvent(
            type="chunk",
            request_id=_REQUEST_ID,
            content="Hello",
        )
        assert event.content == "Hello"

    def test_complete_validates(self) -> None:
        event = DoubtSolverStreamEvent(
            type="complete",
            request_id=_REQUEST_ID,
            stage="complete",
            label="Done",
            metadata={"request_id": _REQUEST_ID},
        )
        assert event.type == "complete"

    def test_error_validates(self) -> None:
        event = DoubtSolverStreamEvent(
            type="error",
            request_id=_REQUEST_ID,
            stage="error",
            label="Something went wrong. Please try again.",
        )
        assert event.type == "error"

    def test_chunk_requires_content(self) -> None:
        with pytest.raises(ValueError, match="chunk event must have content"):
            DoubtSolverStreamEvent(type="chunk", request_id=_REQUEST_ID)

    def test_status_requires_stage_and_label(self) -> None:
        with pytest.raises(ValueError, match="status event must have stage and label"):
            DoubtSolverStreamEvent(
                type="status",
                request_id=_REQUEST_ID,
                stage="understanding",
            )

    def test_error_requires_label(self) -> None:
        with pytest.raises(ValueError, match="error event must have"):
            DoubtSolverStreamEvent(type="error", request_id=_REQUEST_ID, stage="error")

    def test_forbidden_metadata_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="forbidden key"):
            DoubtSolverStreamEvent(
                type="complete",
                request_id=_REQUEST_ID,
                stage="complete",
                label="Done",
                metadata={"prompt": "hidden"},
            )


class TestStreamLabelHelper:
    def test_understanding(self) -> None:
        assert get_stream_label("understanding") == "Understanding..."

    def test_thinking(self) -> None:
        assert get_stream_label("thinking") == "Thinking..."

    def test_solve(self) -> None:
        assert get_stream_label("generating", "solve") == "Solving..."

    def test_explain(self) -> None:
        assert get_stream_label("generating", "explain") == "Explaining..."

    def test_practice(self) -> None:
        assert get_stream_label("generating", "practice") == "Creating practice questions..."

    def test_visualize(self) -> None:
        assert get_stream_label("generating", "visualize") == "Preparing visual explanation..."


class TestStreamingFlow:
    def test_first_event_is_understanding(self) -> None:
        events = _collect(_make_adapter())
        assert events[0].type == "status"
        assert events[0].label == "Understanding..."

    def test_stream_lifecycle_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.INFO):
            _collect(_make_adapter("Short answer."))

        messages = " ".join(r.message for r in caplog.records)
        assert "stream_started=true" in messages
        assert "status_emitted" in messages
        assert "first_chunk_emitted=true" in messages
        assert "stream_completed=true" in messages
        assert "chunk_count=" in messages
        assert "latency_ms=" in messages

    def test_thinking_before_generation(self) -> None:
        events = _collect(_make_adapter())
        status_events = [e for e in events if e.type == "status"]
        labels = [e.label for e in status_events]
        assert "Thinking..." in labels
        assert labels.index("Thinking...") < next(
            i for i, label in enumerate(labels) if label == "Finalizing..."
        )

    def test_chunks_after_generating_status(self) -> None:
        events = _collect(_make_adapter("Alpha beta gamma"))
        generating_idx = next(
            i for i, e in enumerate(events) if e.type == "status" and e.stage == "generating"
        )
        first_chunk_idx = next(i for i, e in enumerate(events) if e.type == "chunk")
        assert first_chunk_idx > generating_idx

    def test_final_event_is_complete(self) -> None:
        events = _collect(_make_adapter())
        assert events[-1].type == "complete"
        assert events[-1].label == "Done"

    def test_chunk_content_is_provider_chunk_content(self) -> None:
        content = "Let the cost price be ₹100. Marked price = ₹140."
        events = _collect(_make_adapter(content))
        chunks = [e.content for e in events if e.type == "chunk"]
        assert "".join(c for c in chunks if c is not None) == content

    def test_no_sensitive_data_in_events(self) -> None:
        events = _collect(_make_adapter("Safe answer text."))
        for event in events:
            blob = f"{event.label or ''} {event.content or ''} {event.metadata}".lower()
            for forbidden in _FORBIDDEN_CONTENT_SUBSTRINGS:
                assert forbidden not in blob


class TestMockProviderStreaming:
    def test_deterministic_chunks_emitted(self) -> None:
        events = _collect(_make_adapter("12345678901234567890"))
        chunks = [e for e in events if e.type == "chunk"]
        assert len(chunks) >= 2

    def test_collected_chunks_equal_final_answer(self) -> None:
        content = "Mock streaming answer for tests."
        events = _collect(_make_adapter(content))
        reconstructed = "".join(e.content or "" for e in events if e.type == "chunk")
        assert reconstructed == content


class TestAzureV1StreamingAdapter:
    def test_fake_streaming_response_yields_chunks(self, tmp_path) -> None:
        from services.llm.providers.azure_openai_provider import AzureOpenAIProviderAdapter
        from services.secrets.provider_credentials import ProviderCredentials
        from tests.test_azure_openai_provider_adapter import _factory, _make_request

        class _FakeStreamChunk:
            def __init__(self, delta: str) -> None:
                self.choices = [types.SimpleNamespace(delta=types.SimpleNamespace(content=delta))]

        class _FakeStreamClient:
            def __init__(self) -> None:
                self.received_kwargs: dict = {}

            @property
            def chat(self) -> types.SimpleNamespace:
                def _create(**kwargs):  # noqa: ANN202
                    self.received_kwargs = kwargs
                    return iter([
                        _FakeStreamChunk("Let "),
                        _FakeStreamChunk("the "),
                        _FakeStreamChunk("cost"),
                    ])

                return types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=_create)
                )

        client = _FakeStreamClient()
        adapter = AzureOpenAIProviderAdapter(client_factory=_factory(client))
        creds = ProviderCredentials(
            provider="azure_openai",
            api_key="fake-key",
            endpoint="https://fake.openai.azure.com/openai/v1",
            azure_api_mode="azure_openai_v1",
        )
        chunks = list(
            adapter.generate_stream(
                request=_make_request(tmp_path),
                credentials=creds,
            )
        )
        assert chunks == ["Let ", "the ", "cost"]
        assert client.received_kwargs.get("model") == "gpt-4o-deployment"
        assert client.received_kwargs.get("stream") is True


class TestNonStreamRegression:
    def test_generate_unchanged(self) -> None:
        content = "Non-streaming answer."
        adapter = _make_adapter(content)
        result = adapter.generate(
            request_id=_REQUEST_ID,
            query="Test",
            subject="general",
            intent="explain",
            difficulty="default",
            context="",
        )
        assert result == content

    def test_graph_state_five_fields(self) -> None:
        fields = set(OrchestratedDoubtSolverState.__annotations__.keys())
        expected = {"request_id", "query", "classification", "context_text", "answer"}
        assert fields == expected

    def test_task_role_remains_generator(self) -> None:
        orchestrator, executor = create_mock_orchestrator_for_tests(content="x")
        adapter = AnswerGenerationAdapter(orchestrator=orchestrator)
        adapter.generate(
            request_id=_REQUEST_ID,
            query="Test",
            subject="math",
            intent="solve",
            difficulty="default",
            context="",
        )
        assert executor.last_route_decision is not None
        assert executor.last_route_decision.task_role == "generator"


class TestStreamingErrorHandling:
    def test_provider_stream_error_returns_safe_error_event(self) -> None:
        events = _collect(_make_adapter(raise_on_execute=RuntimeError("provider boom")))
        assert events[-1].type == "error"
        assert events[-1].label == "Something went wrong. Please try again."

    def test_no_stack_trace_exposed(self) -> None:
        events = _collect(_make_adapter(raise_on_execute=RuntimeError("detailed failure")))
        for event in events:
            blob = f"{event.label or ''} {event.content or ''}"
            assert "Traceback" not in blob
            assert "RuntimeError" not in blob

    def test_no_complete_on_error(self) -> None:
        events = _collect(_make_adapter(raise_on_execute=RuntimeError("fail")))
        assert not any(e.type == "complete" for e in events)
