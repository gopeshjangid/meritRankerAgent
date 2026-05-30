"""
app/services/streaming_adapter.py
----------------------------------
Foundation streaming adapter — converts completed AnswerOutput objects or raw
text-chunk iterables into a stable, provider-neutral stream of StreamEvent objects.

This module is the ONLY place in the application that produces StreamEvent instances.
Graph nodes and main.py must not construct StreamEvent directly.

Public API
----------
stream_answer_output(request_id, answer_output) -> Iterator[StreamEvent]
    Convert a completed AnswerOutput into a word-level stream.
    Order: metadata → content_delta (one per word) → final.

stream_text_chunks(request_id, chunks, metadata=None) -> Iterator[StreamEvent]
    Convert an arbitrary Iterable[str] of chunks into a stream.
    Order: metadata → content_delta per chunk → final.

Design notes
------------
- Both functions are pure generators — no I/O, no model calls, no threads.
- metadata dict MUST NOT contain secrets, API keys, or full provider config.
- _sanitise_metadata enforces:
    (a) allowlist — only {request_id, answer_source, model_label, provider, is_truncated}
    (b) primitive-only values — nested dicts/lists/objects are dropped
    (c) string values truncated to _MAX_METADATA_STR_LEN (200 chars)
    This prevents accidental leakage of prompts, queries, answers, or credentials.
- Empty answer / empty chunk iterator is handled safely:
    stream_answer_output falls back to a single-space content_delta so that
    the AnswerOutput min_length=1 contract is never violated.
    stream_text_chunks handles an empty iterable by emitting metadata + final only.
- [NOT VERIFIED] AgentCore HTTP streaming — these generators produce Python iterables.
  Wiring them to the BedrockAgentCoreApp response is not yet implemented or tested.
- [NOT VERIFIED] Real provider streaming end-to-end.

Streaming distinction
---------------------
Three separate concepts — do not conflate:
  1. Simulated streaming  — stream_answer_output() word-splits a completed AnswerOutput.
  2. Provider streaming   — model_router.stream() yields LlmStreamChunk from a real model.
  3. AgentCore HTTP streaming — BedrockAgentCoreApp chunked HTTP transport [NOT VERIFIED].
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Any

from schemas.doubt_solver import AnswerOutput
from schemas.streaming import StreamEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SAFE_METADATA_KEYS = frozenset(
    {"request_id", "answer_source", "model_label", "provider", "is_truncated"}
)

# Maximum number of characters for any string value in sanitised metadata.
# Prevents full prompts, queries, or answers from leaking through metadata fields.
_MAX_METADATA_STR_LEN = 200

# Allowed primitive types for metadata values.
# Nested dicts, lists, objects, bytes, and any other types are dropped.
_ALLOWED_VALUE_TYPES = (str, int, float, bool, type(None))


def _sanitise_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a hardened copy of *raw* safe for inclusion in StreamEvent.metadata.

    Three-layer defence:
    1. Allowlist  — only keys in ``_SAFE_METADATA_KEYS`` are retained.
    2. Type gate  — values that are not str/int/float/bool/None are dropped.
                    This prevents nested dicts, lists, and SDK objects leaking.
    3. Length cap — string values longer than ``_MAX_METADATA_STR_LEN`` chars
                    are truncated.  Prevents full prompts, queries, or answers
                    from appearing in stream metadata.

    The original dict is never mutated.
    """
    result: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in _SAFE_METADATA_KEYS:
            continue
        if not isinstance(v, _ALLOWED_VALUE_TYPES):
            # Drop nested dicts, lists, objects — they should never be in metadata.
            logger.debug(
                "streaming_adapter._sanitise_metadata: dropped key=%r type=%s",
                k,
                type(v).__name__,
            )
            continue
        if isinstance(v, str) and len(v) > _MAX_METADATA_STR_LEN:
            v = v[:_MAX_METADATA_STR_LEN]
        result[k] = v
    return result


def _make_metadata_event(request_id: str, metadata: dict[str, Any]) -> StreamEvent:
    return StreamEvent(
        event_type="metadata",
        request_id=request_id,
        content_delta="",
        metadata=_sanitise_metadata(metadata),
        is_final=False,
    )


def _make_delta_event(request_id: str, delta: str) -> StreamEvent:
    return StreamEvent(
        event_type="content_delta",
        request_id=request_id,
        content_delta=delta,
        metadata={},
        is_final=False,
    )


def _make_final_event(request_id: str) -> StreamEvent:
    return StreamEvent(
        event_type="final",
        request_id=request_id,
        content_delta="",
        metadata={},
        is_final=True,
    )


def _make_error_event(request_id: str, reason: str) -> StreamEvent:
    """Produce an error terminal event.

    *reason* is a short safe description — MUST NOT contain secrets or PII.
    """
    return StreamEvent(
        event_type="error",
        request_id=request_id,
        content_delta="",
        metadata={"error": reason},
        is_final=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def stream_answer_output(
    request_id: str,
    answer_output: AnswerOutput,
) -> Iterator[StreamEvent]:
    """Convert a completed AnswerOutput into a word-level event stream.

    Emits::

        StreamEvent(event_type="metadata", metadata={answer_source, is_truncated})
        StreamEvent(event_type="content_delta", content_delta="<word> ") × N
        StreamEvent(event_type="final", is_final=True)

    Args:
        request_id:    Trace UUID from the originating request.
        answer_output: Validated AnswerOutput from answer_generator_service.

    Yields:
        StreamEvent instances in the order above.
    """
    logger.debug(
        "streaming_adapter.stream_answer_output  request_id=%s  source=%s  len=%d",
        request_id,
        answer_output.answer_source,
        len(answer_output.content),
    )

    yield _make_metadata_event(
        request_id,
        {
            "request_id": request_id,
            "answer_source": answer_output.answer_source,
            "is_truncated": answer_output.is_truncated,
        },
    )

    words = answer_output.content.split()
    if not words:
        # AnswerOutput.content has min_length=1 so this branch is a safety net only.
        yield _make_delta_event(request_id, answer_output.content)
    else:
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            delta = word if is_last else word + " "
            yield _make_delta_event(request_id, delta)

    yield _make_final_event(request_id)


def stream_text_chunks(
    request_id: str,
    chunks: Iterable[str],
    metadata: dict[str, Any] | None = None,
) -> Iterator[StreamEvent]:
    """Convert an arbitrary text-chunk iterable into a StreamEvent stream.

    Emits::

        StreamEvent(event_type="metadata", metadata=<sanitised metadata>)
        StreamEvent(event_type="content_delta", content_delta="<chunk>") × N
        StreamEvent(event_type="final", is_final=True)

    An empty *chunks* iterable produces metadata + final only (no delta events).

    Args:
        request_id: Trace UUID from the originating request.
        chunks:     Iterable of text chunks (e.g. from model_router.stream).
        metadata:   Optional dict of SAFE tracing values.  Will be sanitised
                    before emission — only allowed keys are kept.

    Yields:
        StreamEvent instances in the order above.
    """
    logger.debug(
        "streaming_adapter.stream_text_chunks  request_id=%s",
        request_id,
    )

    yield _make_metadata_event(request_id, metadata or {})

    for chunk in chunks:
        if chunk:  # skip empty string chunks
            yield _make_delta_event(request_id, chunk)

    yield _make_final_event(request_id)
