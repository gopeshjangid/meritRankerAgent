"""
app/tests/test_streaming_adapter.py
-------------------------------------
Tests for app/services/streaming_adapter.py and app/schemas/streaming.py.

No network calls, no real LLM, no AWS credentials required.
"""

from __future__ import annotations

import pytest

from schemas.doubt_solver import AnswerOutput
from schemas.streaming import StreamEvent
from services.streaming_adapter import (
    _MAX_METADATA_STR_LEN,
    _SAFE_METADATA_KEYS,
    _make_error_event,
    _sanitise_metadata,
    stream_answer_output,
    stream_text_chunks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUEST_ID = "test-req-00000000-0000-0000-0000-000000000001"


def _make_answer_output(
    content: str = "Hello world from the answer generator.",
    answer_source: str = "mock",
    is_truncated: bool = False,
) -> AnswerOutput:
    return AnswerOutput(content=content, answer_source=answer_source, is_truncated=is_truncated)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# StreamEvent schema
# ---------------------------------------------------------------------------


class TestStreamEventSchema:
    def test_metadata_event_valid(self):
        evt = StreamEvent(
            event_type="metadata",
            request_id=REQUEST_ID,
            metadata={"answer_source": "mock"},
        )
        assert evt.event_type == "metadata"
        assert evt.is_final is False
        assert evt.content_delta == ""

    def test_content_delta_event_valid(self):
        evt = StreamEvent(
            event_type="content_delta",
            request_id=REQUEST_ID,
            content_delta="Hello ",
        )
        assert evt.event_type == "content_delta"
        assert evt.content_delta == "Hello "
        assert evt.is_final is False

    def test_final_event_valid(self):
        evt = StreamEvent(
            event_type="final",
            request_id=REQUEST_ID,
            is_final=True,
        )
        assert evt.event_type == "final"
        assert evt.is_final is True
        assert evt.content_delta == ""

    def test_error_event_valid(self):
        evt = StreamEvent(
            event_type="error",
            request_id=REQUEST_ID,
            metadata={"error": "generator_failed"},
            is_final=True,
        )
        assert evt.event_type == "error"
        assert evt.is_final is True

    def test_invalid_event_type_raises(self):
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            StreamEvent(event_type="unknown", request_id=REQUEST_ID)  # type: ignore[arg-type]

    def test_missing_request_id_raises(self):
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            StreamEvent(event_type="metadata")  # type: ignore[call-arg]

    def test_metadata_defaults_to_empty_dict(self):
        evt = StreamEvent(event_type="final", request_id=REQUEST_ID, is_final=True)
        assert evt.metadata == {}

    def test_is_final_defaults_to_false(self):
        evt = StreamEvent(event_type="metadata", request_id=REQUEST_ID)
        assert evt.is_final is False

    def test_content_delta_defaults_to_empty_string(self):
        evt = StreamEvent(event_type="metadata", request_id=REQUEST_ID)
        assert evt.content_delta == ""


# ---------------------------------------------------------------------------
# _sanitise_metadata
# ---------------------------------------------------------------------------


class TestSanitiseMetadata:
    def test_allowed_keys_pass_through(self):
        raw = {
            "request_id": REQUEST_ID,
            "answer_source": "mock",
            "model_label": "gpt-4o",
            "provider": "openai",
            "is_truncated": False,
        }
        result = _sanitise_metadata(raw)
        assert result == raw

    def test_secret_keys_are_removed(self):
        raw = {
            "request_id": REQUEST_ID,
            "api_key": "sk-super-secret",
            "answer_source": "mock",
            "azure_endpoint": "https://example.openai.azure.com/",
            "password": "hunter2",
        }
        result = _sanitise_metadata(raw)
        assert "api_key" not in result
        assert "azure_endpoint" not in result
        assert "password" not in result
        assert result["request_id"] == REQUEST_ID
        assert result["answer_source"] == "mock"

    def test_empty_dict_stays_empty(self):
        assert _sanitise_metadata({}) == {}

    def test_unknown_keys_are_removed(self):
        raw = {"unknown_field": "value", "answer_source": "llm"}
        result = _sanitise_metadata(raw)
        assert "unknown_field" not in result
        assert result["answer_source"] == "llm"

    def test_does_not_mutate_original(self):
        raw = {"request_id": REQUEST_ID, "api_key": "secret"}
        original_keys = set(raw.keys())
        _sanitise_metadata(raw)
        assert set(raw.keys()) == original_keys


# ---------------------------------------------------------------------------
# stream_answer_output
# ---------------------------------------------------------------------------


class TestStreamAnswerOutput:
    def test_first_event_is_metadata(self):
        output = _make_answer_output("Hello world")
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].event_type == "metadata"

    def test_last_event_is_final(self):
        output = _make_answer_output("Hello world")
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[-1].event_type == "final"
        assert events[-1].is_final is True

    def test_last_event_is_final_not_content_delta(self):
        output = _make_answer_output("Hello world")
        events = list(stream_answer_output(REQUEST_ID, output))
        last = events[-1]
        assert last.event_type == "final"
        assert last.content_delta == ""

    def test_content_deltas_reconstruct_original_answer(self):
        original = "What is the capital of France? Paris is the answer."
        output = _make_answer_output(original)
        events = list(stream_answer_output(REQUEST_ID, output))
        delta_events = [e for e in events if e.event_type == "content_delta"]
        reconstructed = "".join(e.content_delta for e in delta_events)
        assert reconstructed == original

    def test_metadata_event_carries_answer_source(self):
        output = _make_answer_output("Some answer", answer_source="mock")
        events = list(stream_answer_output(REQUEST_ID, output))
        meta = events[0]
        assert meta.event_type == "metadata"
        assert meta.metadata.get("answer_source") == "mock"

    def test_metadata_event_carries_is_truncated(self):
        output = _make_answer_output("Some answer", is_truncated=True)
        events = list(stream_answer_output(REQUEST_ID, output))
        meta = events[0]
        assert meta.metadata.get("is_truncated") is True

    def test_metadata_does_not_contain_secrets(self):
        output = _make_answer_output("Answer text")
        events = list(stream_answer_output(REQUEST_ID, output))
        meta_dict = events[0].metadata
        forbidden = {"api_key", "azure_endpoint", "password", "secret", "token"}
        assert not (forbidden & set(meta_dict.keys()))

    def test_all_events_have_correct_request_id(self):
        output = _make_answer_output("Testing request_id propagation")
        events = list(stream_answer_output(REQUEST_ID, output))
        for evt in events:
            assert evt.request_id == REQUEST_ID

    def test_single_word_answer_produces_three_events(self):
        """metadata + one content_delta + final = 3 events."""
        output = _make_answer_output("Fraction")
        events = list(stream_answer_output(REQUEST_ID, output))
        types = [e.event_type for e in events]
        assert types == ["metadata", "content_delta", "final"]

    def test_multi_word_answer_produces_correct_delta_count(self):
        answer = "The answer is forty two"
        output = _make_answer_output(answer)
        events = list(stream_answer_output(REQUEST_ID, output))
        delta_events = [e for e in events if e.event_type == "content_delta"]
        assert len(delta_events) == len(answer.split())

    def test_llm_source_propagated_in_metadata(self):
        output = _make_answer_output("LLM-generated answer", answer_source="llm")
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].metadata.get("answer_source") == "llm"

    def test_fallback_source_propagated_in_metadata(self):
        output = _make_answer_output("Fallback answer", answer_source="fallback")
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].metadata.get("answer_source") == "fallback"

    def test_minimum_event_count_is_three(self):
        """Every call must emit at least metadata + 1 delta + final."""
        output = _make_answer_output("x")  # single char
        events = list(stream_answer_output(REQUEST_ID, output))
        assert len(events) >= 3

    def test_events_are_stream_event_instances(self):
        output = _make_answer_output("Check types")
        for evt in stream_answer_output(REQUEST_ID, output):
            assert isinstance(evt, StreamEvent)


# ---------------------------------------------------------------------------
# stream_text_chunks
# ---------------------------------------------------------------------------


class TestStreamTextChunks:
    def test_first_event_is_metadata(self):
        events = list(stream_text_chunks(REQUEST_ID, ["Hello", " world"]))
        assert events[0].event_type == "metadata"

    def test_last_event_is_final(self):
        events = list(stream_text_chunks(REQUEST_ID, ["Hello", " world"]))
        assert events[-1].event_type == "final"
        assert events[-1].is_final is True

    def test_chunks_become_content_delta_events(self):
        chunks = ["The ", "quick ", "brown ", "fox"]
        events = list(stream_text_chunks(REQUEST_ID, chunks))
        delta_events = [e for e in events if e.event_type == "content_delta"]
        assert len(delta_events) == len(chunks)
        reconstructed = "".join(e.content_delta for e in delta_events)
        assert reconstructed == "".join(chunks)

    def test_empty_chunks_produces_only_metadata_and_final(self):
        events = list(stream_text_chunks(REQUEST_ID, []))
        types = [e.event_type for e in events]
        assert types == ["metadata", "final"]

    def test_empty_string_chunks_are_skipped(self):
        """Empty string chunks must not produce content_delta events."""
        events = list(stream_text_chunks(REQUEST_ID, ["", "", "hello", ""]))
        delta_events = [e for e in events if e.event_type == "content_delta"]
        assert len(delta_events) == 1
        assert delta_events[0].content_delta == "hello"

    def test_metadata_kwarg_is_sanitised(self):
        meta = {"answer_source": "llm", "api_key": "should-be-removed"}
        events = list(stream_text_chunks(REQUEST_ID, ["chunk"], metadata=meta))
        assert "api_key" not in events[0].metadata
        assert events[0].metadata.get("answer_source") == "llm"

    def test_none_metadata_produces_empty_dict(self):
        events = list(stream_text_chunks(REQUEST_ID, ["x"], metadata=None))
        assert events[0].metadata == {}

    def test_all_events_have_correct_request_id(self):
        events = list(stream_text_chunks(REQUEST_ID, ["a", "b"]))
        for evt in events:
            assert evt.request_id == REQUEST_ID

    def test_events_are_stream_event_instances(self):
        for evt in stream_text_chunks(REQUEST_ID, ["hello"]):
            assert isinstance(evt, StreamEvent)

    def test_generator_from_iterator(self):
        """Works with a lazy generator, not just a list."""

        def lazy():
            yield "word1 "
            yield "word2"

        events = list(stream_text_chunks(REQUEST_ID, lazy()))
        delta_events = [e for e in events if e.event_type == "content_delta"]
        assert len(delta_events) == 2


# ---------------------------------------------------------------------------
# _make_error_event
# ---------------------------------------------------------------------------


class TestMakeErrorEvent:
    def test_error_event_type(self):
        evt = _make_error_event(REQUEST_ID, "generation_failed")
        assert evt.event_type == "error"

    def test_error_event_is_final(self):
        evt = _make_error_event(REQUEST_ID, "generation_failed")
        assert evt.is_final is True

    def test_error_event_metadata_has_error_key(self):
        evt = _make_error_event(REQUEST_ID, "something_went_wrong")
        assert "error" in evt.metadata

    def test_error_reason_in_metadata(self):
        evt = _make_error_event(REQUEST_ID, "timeout")
        assert evt.metadata["error"] == "timeout"

    def test_error_event_has_empty_content_delta(self):
        evt = _make_error_event(REQUEST_ID, "timeout")
        assert evt.content_delta == ""


# ---------------------------------------------------------------------------
# model_router.stream with mock provider (no real LLM)
# ---------------------------------------------------------------------------


class TestModelRouterStreamMock:
    """Verify model_router.stream works with the mock provider.

    ENABLE_REAL_LLM defaults to false → mock provider is used.
    No real AWS/OpenAI/Azure credentials required.

    [NOT VERIFIED] Real provider streaming (azure_openai / openai) is not
                   tested here.
    """

    def test_stream_yields_lllm_stream_chunks(self):
        from schemas.llm import LlmMessage, LlmStreamChunk  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="Hello streaming")]
        chunks = list(model_router.stream("doubt_solver_generator", messages))
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, LlmStreamChunk)

    def test_stream_last_chunk_is_final(self):
        from schemas.llm import LlmMessage  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="Test final chunk")]
        chunks = list(model_router.stream("doubt_solver_generator", messages))
        assert chunks[-1].is_final is True

    def test_stream_chunks_reconstruct_content(self):
        from schemas.llm import LlmMessage  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="Reconstruct me")]
        chunks = list(model_router.stream("doubt_solver_generator", messages))
        full = "".join(c.content_delta for c in chunks)
        assert len(full) > 0

    def test_stream_text_chunks_from_model_router(self):
        """End-to-end: model_router.stream → stream_text_chunks → StreamEvent list."""
        from schemas.llm import LlmMessage  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="E2E streaming test")]
        raw_chunks = (
            c.content_delta
            for c in model_router.stream("doubt_solver_generator", messages)
        )
        events = list(
            stream_text_chunks(REQUEST_ID, raw_chunks, metadata={"answer_source": "mock"})
        )
        assert events[0].event_type == "metadata"
        assert events[-1].event_type == "final"
        assert events[-1].is_final is True
        delta_events = [e for e in events if e.event_type == "content_delta"]
        assert len(delta_events) > 0


# ---------------------------------------------------------------------------
# Part 6: _sanitise_metadata hardening — nested values, long strings, types
# ---------------------------------------------------------------------------


class TestSanitiseMetadataHardening:
    """Tests for Part 6 hardening: type gate + string length cap."""

    def test_nested_dict_value_is_dropped(self):
        """A nested dict must not pass through — even if the key is allowed."""
        raw = {"answer_source": {"nested": "value"}, "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert "answer_source" not in result
        assert result["provider"] == "mock"

    def test_list_value_is_dropped(self):
        raw = {"answer_source": ["item1", "item2"], "provider": "openai"}
        result = _sanitise_metadata(raw)
        assert "answer_source" not in result
        assert result["provider"] == "openai"

    def test_object_value_is_dropped(self):
        """Custom objects (non-primitive) must not appear in sanitised metadata."""

        class _Obj:
            pass

        raw = {"model_label": _Obj(), "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert "model_label" not in result
        assert result["provider"] == "mock"

    def test_bytes_value_is_dropped(self):
        raw = {"model_label": b"gpt-4o", "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert "model_label" not in result

    def test_int_value_passes(self):
        raw = {"model_label": 42, "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert result["model_label"] == 42

    def test_float_value_passes(self):
        raw = {"is_truncated": 0.99, "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert result["is_truncated"] == 0.99

    def test_bool_value_passes(self):
        raw = {"is_truncated": True}
        result = _sanitise_metadata(raw)
        assert result["is_truncated"] is True

    def test_none_value_passes(self):
        raw = {"model_label": None, "provider": "mock"}
        result = _sanitise_metadata(raw)
        assert result["model_label"] is None

    def test_long_string_is_truncated(self):
        long_value = "x" * (_MAX_METADATA_STR_LEN + 100)
        raw = {"model_label": long_value}
        result = _sanitise_metadata(raw)
        assert len(result["model_label"]) == _MAX_METADATA_STR_LEN

    def test_string_at_exact_limit_is_not_truncated(self):
        exact_value = "a" * _MAX_METADATA_STR_LEN
        raw = {"model_label": exact_value}
        result = _sanitise_metadata(raw)
        assert len(result["model_label"]) == _MAX_METADATA_STR_LEN

    def test_string_below_limit_is_unchanged(self):
        short = "gpt-4o-mini"
        raw = {"model_label": short}
        result = _sanitise_metadata(raw)
        assert result["model_label"] == short

    def test_full_prompt_in_allowed_key_is_truncated(self):
        """A full prompt accidentally placed in an allowed key is truncated."""
        prompt = "You are a math tutor. " * 50  # >> 200 chars
        raw = {"model_label": prompt}
        result = _sanitise_metadata(raw)
        assert len(result["model_label"]) <= _MAX_METADATA_STR_LEN

    def test_all_secret_adjacent_keys_removed(self):
        """Keys not in the allowlist are always removed regardless of value type."""
        raw = {
            "api_key": "sk-secret",
            "azure_endpoint": "https://example.openai.azure.com/",
            "deployment": "gpt-4o-prod",
            "password": "hunter2",
            "full_query": "What is the answer?",
            "full_answer": "The answer is 42.",
            "config": {"provider": "openai"},
            "answer_source": "mock",  # the only valid key in this set
        }
        result = _sanitise_metadata(raw)
        allowed_in_result = set(result.keys()) & _SAFE_METADATA_KEYS
        forbidden_in_result = set(result.keys()) - _SAFE_METADATA_KEYS
        assert not forbidden_in_result
        assert allowed_in_result == {"answer_source"}

    def test_does_not_mutate_original_with_nested(self):
        raw = {"answer_source": {"deep": "object"}, "provider": "mock"}
        original = dict(raw)
        _sanitise_metadata(raw)
        assert raw == original

    def test_stream_answer_output_metadata_passes_type_gate(self):
        """Metadata emitted by stream_answer_output must contain only safe primitives."""
        output = AnswerOutput(  # type: ignore[call-arg]
            content="Test answer for type gate",
            answer_source="mock",
            is_truncated=False,
        )
        events = list(stream_answer_output(REQUEST_ID, output))
        meta = events[0].metadata
        for k, v in meta.items():
            assert isinstance(v, (str, int, float, bool, type(None))), (
                f"metadata key {k!r} has non-primitive value {type(v).__name__}"
            )

    def test_stream_text_chunks_metadata_passes_type_gate(self):
        """Metadata passed to stream_text_chunks is sanitised before emission."""
        unsafe_meta = {
            "answer_source": "mock",
            "internal_config": {"key": "value"},  # nested — should be dropped
        }
        events = list(stream_text_chunks(REQUEST_ID, ["hello"], metadata=unsafe_meta))
        meta = events[0].metadata
        assert "internal_config" not in meta
        assert meta.get("answer_source") == "mock"


# ---------------------------------------------------------------------------
# Streaming distinction — simulated vs provider vs AgentCore HTTP
# ---------------------------------------------------------------------------


class TestStreamingDistinction:
    """Document and verify the three streaming types are clearly distinct.

    1. Simulated  — stream_answer_output() word-splits a *completed* AnswerOutput.
    2. Provider   — model_router.stream() yields LlmStreamChunk from a real/mock model.
    3. AgentCore  — BedrockAgentCoreApp HTTP chunked transport [NOT VERIFIED].
    """

    def test_simulated_streaming_uses_completed_answer(self):
        """stream_answer_output receives a fully-formed AnswerOutput — not raw model chunks."""
        # The content is already complete before streaming begins.
        content = "Paris is the capital of France."
        output = AnswerOutput(content=content, answer_source="mock", is_truncated=False)  # type: ignore[call-arg]
        events = list(stream_answer_output(REQUEST_ID, output))
        reconstructed = "".join(e.content_delta for e in events if e.event_type == "content_delta")
        assert reconstructed == content  # full content was available before first event

    def test_simulated_streaming_is_not_provider_streaming(self):
        """stream_answer_output events have no LlmStreamChunk fields."""
        output = AnswerOutput(content="Test content", answer_source="mock", is_truncated=False)  # type: ignore[call-arg]
        for evt in stream_answer_output(REQUEST_ID, output):
            assert isinstance(evt, StreamEvent)
            assert not hasattr(evt, "role")       # LlmStreamChunk field
            assert not hasattr(evt, "content_delta") or isinstance(evt.content_delta, str)

    def test_provider_streaming_yields_llm_stream_chunks(self):
        """model_router.stream yields LlmStreamChunk — a different schema than StreamEvent."""
        from schemas.llm import LlmMessage, LlmStreamChunk  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="Provider streaming test")]
        chunks = list(model_router.stream("doubt_solver_generator", messages))
        for chunk in chunks:
            assert isinstance(chunk, LlmStreamChunk)
            assert not isinstance(chunk, StreamEvent)

    def test_stream_text_chunks_adapts_provider_chunks_to_stream_events(self):
        """stream_text_chunks converts LlmStreamChunk deltas into StreamEvent objects."""
        from schemas.llm import LlmMessage  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        messages = [LlmMessage(role="user", content="Adapter bridge test")]
        raw = (c.content_delta for c in model_router.stream("doubt_solver_generator", messages))
        events = list(stream_text_chunks(REQUEST_ID, raw))
        for evt in events:
            assert isinstance(evt, StreamEvent)


# ---------------------------------------------------------------------------
# runtime_probe_service
# ---------------------------------------------------------------------------


class TestRuntimeProbeService:
    """Tests for app/services/runtime_probe_service.py.

    No network calls — only payload building and shape validation.
    """

    def test_smoke_payload_has_required_keys(self):
        from services.runtime_probe_service import build_doubt_solver_smoke_payload  # noqa: PLC0415

        payload = build_doubt_solver_smoke_payload()
        for key in ("mode", "query", "user_id", "language"):
            assert key in payload, f"missing key: {key!r}"

    def test_smoke_payload_mode_is_doubt_solver(self):
        from services.runtime_probe_service import build_doubt_solver_smoke_payload  # noqa: PLC0415

        payload = build_doubt_solver_smoke_payload()
        assert payload["mode"] == "doubt_solver"

    def test_smoke_payload_query_is_non_empty(self):
        from services.runtime_probe_service import build_doubt_solver_smoke_payload  # noqa: PLC0415

        payload = build_doubt_solver_smoke_payload()
        assert isinstance(payload["query"], str)
        assert len(payload["query"]) > 10

    def test_smoke_payload_language_is_en(self):
        from services.runtime_probe_service import build_doubt_solver_smoke_payload  # noqa: PLC0415

        payload = build_doubt_solver_smoke_payload()
        assert payload["language"] == "en"

    def test_smoke_payload_no_secrets(self):
        from services.runtime_probe_service import build_doubt_solver_smoke_payload  # noqa: PLC0415

        payload = build_doubt_solver_smoke_payload()
        serialised = str(payload)
        for forbidden in ("api_key", "password", "secret", "token", "sk-"):
            assert forbidden not in serialised.lower(), (
                f"smoke payload must not contain {forbidden!r}"
            )

    def test_validate_shape_passes_for_valid_response(self):
        from services.runtime_probe_service import (
            validate_doubt_solver_response_shape,  # noqa: PLC0415
        )

        valid = {
            "success": True,
            "request_id": "00000000-0000-0000-0000-000000000001",
            "mode": "doubt_solver",
            "answer": "The profit is 12%.",
            "classification": {"intent": "solve_question", "confidence": 0.95},
            "needs_review": False,
            "answer_source": "mock",
            "is_truncated": False,
        }
        ok, issues = validate_doubt_solver_response_shape(valid)
        assert ok, issues

    def test_validate_shape_fails_for_missing_field(self):
        from services.runtime_probe_service import (
            validate_doubt_solver_response_shape,  # noqa: PLC0415
        )

        incomplete = {
            "success": True,
            "request_id": "abc",
            "mode": "doubt_solver",
            # missing: answer, classification, needs_review, answer_source, is_truncated
        }
        ok, issues = validate_doubt_solver_response_shape(incomplete)
        assert not ok
        assert len(issues) > 0

    def test_validate_shape_fails_for_invalid_answer_source(self):
        from services.runtime_probe_service import (
            validate_doubt_solver_response_shape,  # noqa: PLC0415
        )

        bad = {
            "success": True,
            "request_id": "abc",
            "mode": "doubt_solver",
            "answer": "Some answer",
            "classification": {"intent": "general_doubt", "confidence": 0.5},
            "needs_review": False,
            "answer_source": "unknown_source",
            "is_truncated": False,
        }
        ok, issues = validate_doubt_solver_response_shape(bad)
        assert not ok
        assert any("answer_source" in i for i in issues)

    def test_validate_shape_fails_for_success_false(self):
        from services.runtime_probe_service import (
            validate_doubt_solver_response_shape,  # noqa: PLC0415
        )

        err_resp = {
            "success": False,
            "request_id": "abc",
            "mode": "doubt_solver",
            "answer": "Validation error: ...",
            "classification": {"intent": "unknown", "confidence": 0.0},
            "needs_review": True,
            "answer_source": "fallback",
            "is_truncated": False,
        }
        ok, issues = validate_doubt_solver_response_shape(err_resp)
        assert not ok
        assert any("False" in i for i in issues)

    def test_validate_shape_notes_missing_classification_subfields(self):
        from services.runtime_probe_service import (
            validate_doubt_solver_response_shape,  # noqa: PLC0415
        )

        partial_cls = {
            "success": True,
            "request_id": "abc",
            "mode": "doubt_solver",
            "answer": "An answer",
            "classification": {"intent": "solve_question"},  # missing confidence
            "needs_review": False,
            "answer_source": "mock",
            "is_truncated": False,
        }
        ok, issues = validate_doubt_solver_response_shape(partial_cls)
        assert not ok
        assert any("confidence" in i for i in issues)

    def test_validate_shape_passes_end_to_end_with_invoke(self):
        """Build smoke payload → main.invoke() → validate response shape."""
        import main  # noqa: PLC0415
        from services.runtime_probe_service import (  # noqa: PLC0415
            build_doubt_solver_smoke_payload,
            validate_doubt_solver_response_shape,
        )

        payload = build_doubt_solver_smoke_payload()
        result = main.invoke(payload)
        ok, issues = validate_doubt_solver_response_shape(result)
        assert ok, f"Response shape validation failed: {issues}"


# ---------------------------------------------------------------------------
# Part 10: Streaming readiness — DoubtSolverResponse → StreamEvent sequence
# ---------------------------------------------------------------------------


class TestStreamingFromDoubtSolverResponse:
    """Verify that a DoubtSolverResponse/AnswerOutput can be converted to a
    valid StreamEvent sequence with the correct shape and safety properties.

    Important distinctions (all three are separate concepts):
        1. Simulated streaming  — stream_answer_output() word-splits a completed
                                  AnswerOutput.  This is what these tests verify.
        2. Provider streaming   — model_router.stream() yields LlmStreamChunk from
                                  a real/mock model (tested in TestModelRouterStreamMock).
        3. AgentCore HTTP streaming — wiring stream generators to BedrockAgentCoreApp
                                     response transport.
                                     [NOT VERIFIED] — not implemented or tested.

    No real AWS, LLM, or network calls required.
    """

    def _answer_output(self, content: str = "Algebra is a branch of mathematics.") -> AnswerOutput:
        return AnswerOutput(  # type: ignore[call-arg]
            content=content, answer_source="mock", is_truncated=False
        )

    def test_metadata_event_carries_request_id(self):
        output = self._answer_output()
        events = list(stream_answer_output(REQUEST_ID, output))
        meta = events[0]
        assert meta.event_type == "metadata"
        assert meta.request_id == REQUEST_ID

    def test_metadata_event_carries_answer_source(self):
        output = AnswerOutput(  # type: ignore[call-arg]
            content="Some answer.", answer_source="llm", is_truncated=False
        )
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].metadata.get("answer_source") == "llm"

    def test_metadata_event_carries_is_truncated_flag(self):
        output = AnswerOutput(  # type: ignore[call-arg]
            content="Truncated answer.", answer_source="mock", is_truncated=True
        )
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].metadata.get("is_truncated") is True

    def test_content_deltas_reconstruct_full_answer(self):
        original = "The shopkeeper marks goods 40% above cost price."
        output = self._answer_output(original)
        events = list(stream_answer_output(REQUEST_ID, output))
        deltas = [e for e in events if e.event_type == "content_delta"]
        assert "".join(e.content_delta for e in deltas) == original

    def test_final_event_is_present_and_marked(self):
        output = self._answer_output()
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[-1].event_type == "final"
        assert events[-1].is_final is True

    def test_sequence_order_is_metadata_deltas_final(self):
        output = self._answer_output("Ratio means comparison.")
        events = list(stream_answer_output(REQUEST_ID, output))
        assert events[0].event_type == "metadata"
        assert events[-1].event_type == "final"
        middle_types = {e.event_type for e in events[1:-1]}
        assert middle_types == {"content_delta"}


class TestStreamingMetadataSafety:
    """Verify that stream metadata never exposes sensitive or oversized data.

    Rules:
        - No full context string
        - No full prompt text
        - No full query text
        - No full retrieved records or KB content
        - No secrets (API keys, endpoints, passwords)
        - Only keys in _SAFE_METADATA_KEYS pass through

    This protects against accidental leakage through the streaming interface.
    """

    def test_metadata_only_contains_safe_keys(self):
        output = _make_answer_output("Some answer", answer_source="mock")
        events = list(stream_answer_output(REQUEST_ID, output))
        meta_keys = set(events[0].metadata.keys())
        assert meta_keys <= _SAFE_METADATA_KEYS, (
            f"Unexpected keys in metadata: {meta_keys - _SAFE_METADATA_KEYS}"
        )

    def test_full_context_string_not_in_metadata(self):
        """A full retrieved context string must not appear in stream metadata."""
        full_context = "A" * 500  # simulate a full context blob
        raw_meta = {
            "answer_source": "mock",
            "context": full_context,  # not an allowed key
        }
        result = _sanitise_metadata(raw_meta)
        assert "context" not in result

    def test_full_prompt_not_in_metadata(self):
        raw_meta = {
            "answer_source": "mock",
            "prompt": "You are a tutor. " * 50,
            "system_prompt": "System instructions...",
        }
        result = _sanitise_metadata(raw_meta)
        assert "prompt" not in result
        assert "system_prompt" not in result

    def test_full_query_not_in_metadata(self):
        raw_meta = {
            "answer_source": "mock",
            "query": "What is the profit percentage when a shopkeeper marks up 40%?",
        }
        result = _sanitise_metadata(raw_meta)
        assert "query" not in result

    def test_retrieved_records_not_in_metadata(self):
        raw_meta = {
            "answer_source": "mock",
            "kb_results": [{"content": "Algebra content..."}],
            "dynamodb_records": [{"question_id": "q-1", "text": "..."}],
        }
        result = _sanitise_metadata(raw_meta)
        assert "kb_results" not in result
        assert "dynamodb_records" not in result

    def test_secret_keys_stripped_from_metadata(self):
        raw_meta = {
            "answer_source": "mock",
            "api_key": "sk-super-secret",
            "azure_openai_api_key": "key-value",
            "aws_secret_access_key": "aws-secret",
        }
        result = _sanitise_metadata(raw_meta)
        for key in ("api_key", "azure_openai_api_key", "aws_secret_access_key"):
            assert key not in result

    def test_long_string_values_truncated(self):
        """String values exceeding _MAX_METADATA_STR_LEN must be truncated."""
        long_model_label = "gpt-" + "x" * 300
        raw_meta = {"model_label": long_model_label, "answer_source": "mock"}
        result = _sanitise_metadata(raw_meta)
        assert len(result["model_label"]) <= _MAX_METADATA_STR_LEN

    def test_stream_events_from_graph_response_have_safe_metadata(self):
        """End-to-end: graph response → AnswerOutput → stream events → safe metadata."""
        import graphs.doubt_solver_graph as graph_module  # noqa: PLC0415

        graph = graph_module.build_doubt_solver_graph()
        graph_state = {
            "request_id": "stream-safety-test",
            "query": "Explain ratio",
            "user_id": "test-user",
            "mode": "doubt_solver",
            "language": "en",
            "classification": None,
            "answer": None,
            "answer_source": None,
            "is_truncated": False,
            "response": None,
            "should_retrieve": False,
            "kb_results": None,
            "dynamodb_records": None,
            "answer_context": None,
            "context_source_count": 0,
            "used_retrieval": False,
            "context_used": False,
            "service_error": False,
        }
        result = graph.invoke(graph_state)
        response = result["response"]

        # Build AnswerOutput from response and stream it.
        output = AnswerOutput(  # type: ignore[call-arg]
            content=response["answer"],
            answer_source=response["answer_source"],
            is_truncated=response["is_truncated"],
        )
        events = list(stream_answer_output(response["request_id"], output))

        # All event metadata must only contain safe keys.
        for evt in events:
            assert set(evt.metadata.keys()) <= _SAFE_METADATA_KEYS


class TestAgentCoreStreamingVerificationChecklist:
    """Documents the verification status of each streaming tier.

    These tests verify the *documented state* of streaming, not runtime behaviour.
    They serve as a living checklist updated with each part.

    [NOT VERIFIED] items must remain as such until manually confirmed.
    """

    def test_simulated_streaming_is_implemented_and_tested(self):
        """stream_answer_output() is implemented and tested — VERIFIED."""
        output = AnswerOutput(  # type: ignore[call-arg]
            content="The answer is 42.", answer_source="mock", is_truncated=False
        )
        events = list(stream_answer_output(REQUEST_ID, output))
        assert len(events) >= 3
        assert events[0].event_type == "metadata"
        assert events[-1].is_final is True

    def test_mock_provider_streaming_is_implemented_and_tested(self):
        """model_router.stream() with mock provider — VERIFIED."""
        from schemas.llm import LlmMessage  # noqa: PLC0415
        from services import model_router  # noqa: PLC0415

        chunks = list(model_router.stream("doubt_solver_generator", [
            LlmMessage(role="user", content="Mock stream test")
        ]))
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_agentcore_http_streaming_not_yet_verified(self):
        """AgentCore HTTP streaming is [NOT VERIFIED] — this test documents that.

        To verify: start `make dev` and confirm the server returns chunked
        responses when invoke() returns a generator or stream adapter output.

        Checklist (all NOT VERIFIED):
            - provider stream works (real azure_openai / openai) [NOT VERIFIED]
            - model_router.stream() with real provider [NOT VERIFIED]
            - BedrockAgentCoreApp accepts iterable/chunked response [NOT VERIFIED]
            - local HTTP client (curl) receives progressively [NOT VERIFIED]
            - frontend can consume server-sent events or streaming JSON [NOT VERIFIED]

        This test always passes to document the status.
        """
        # This assertion is intentionally trivial — it documents intent only.
        assert True, "AgentCore HTTP streaming is [NOT VERIFIED] — see docstring"

