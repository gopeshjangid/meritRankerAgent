"""
app/services/doubt_solver/streaming_doubt_solver_service.py
-------------------------------------------------------------
Student-friendly streaming for the orchestrated doubt solver.

Mirrors the orchestrated graph flow without expanding graph state:
    understanding → classify → thinking → collect context → generating →
    stream chunks → finalizing → complete

Streaming is out-of-band from LangGraph state — graph state remains exactly
request_id, query, classification, context_text, answer.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass

from graphs.doubt_solver_graph import (
    _ORCHESTRATED_FALLBACK_CLASSIFICATION,
    _orchestrated_collect_context_node,
    orchestrated_classify_query,
)
from schemas.doubt_solver import DoubtSolverStreamEvent
from services.doubt_solver.answer_generation_adapter import AnswerGenerationAdapter
from services.doubt_solver.stream_labels import (
    LABEL_ANSWER_CONTINUATION,
    LABEL_CAREFUL_CLASSIFICATION,
    LABEL_GENERATOR_FALLBACK,
    LABEL_WEB_SEARCH,
    LABEL_WEB_SEARCH_RETRY,
    LABEL_WEB_SEARCH_WEAK,
    get_stream_label,
)
from services.doubt_solver.stream_status import StreamStatusTracker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamDoubtSolverInput:
    """Input for orchestrated doubt solver streaming."""

    request_id: str
    query: str


def _status_event(
    *,
    request_id: str,
    stage: str,
    intent: str | None = None,
    label: str | None = None,
) -> DoubtSolverStreamEvent:
    return DoubtSolverStreamEvent(
        type="status",
        request_id=request_id,
        stage=stage,
        label=label or get_stream_label(stage, intent),
    )


def stream_doubt_solver(
    input: StreamDoubtSolverInput,
    *,
    adapter: AnswerGenerationAdapter,
) -> Iterator[DoubtSolverStreamEvent]:
    """Stream student-friendly status labels and real answer chunks.

    Args:
        input:   request_id and query for the doubt solver request.
        adapter: AnswerGenerationAdapter wired to the orchestrator chain.

    Yields:
        DoubtSolverStreamEvent instances in order: status, chunks, complete.
        On failure: status events followed by a safe error event.
    """
    request_id = input.request_id
    query = input.query
    started_at = time.monotonic()
    first_chunk_logged = False
    status_tracker = StreamStatusTracker(request_id=request_id)

    logger.info(
        "streaming_doubt_solver  request_id=%s  stream_started=true",
        request_id,
    )

    def _emit_status(
        *,
        stage: str,
        intent: str | None = None,
        label: str | None = None,
        reason_code: str = "stage_progress",
    ) -> DoubtSolverStreamEvent | None:
        """Return a status event for immediate yield, or None if deduped."""
        resolved_label = label or get_stream_label(stage, intent)
        event = status_tracker.emit_direct(
            stage=stage,
            label=resolved_label,
            reason_code=reason_code,
        )
        if event is not None:
            logger.info(
                "streaming_doubt_solver  request_id=%s  status_emitted  stage=%s",
                request_id,
                stage,
            )
        return event

    event = _emit_status(stage="understanding", reason_code="stream_started")
    if event is not None:
        yield event

    state = {
        "request_id": request_id,
        "query": query,
        "classification": None,
        "context_text": "",
        "answer": None,
    }

    careful_status_pending = False

    def _on_before_strong_classifier() -> None:
        nonlocal careful_status_pending
        careful_status_pending = True

    classification_dict = orchestrated_classify_query(
        query,
        request_id=request_id,
        on_before_strong_classifier=_on_before_strong_classifier,
    )
    state["classification"] = classification_dict

    if careful_status_pending:
        careful_event = _emit_status(
            stage="understanding",
            label=LABEL_CAREFUL_CLASSIFICATION,
            reason_code="classifier_fallback",
        )
        if careful_event is not None:
            yield careful_event

    thinking_event = _emit_status(stage="thinking", reason_code="thinking")
    if thinking_event is not None:
        yield thinking_event

    need_web_search = bool(classification_dict.get("need_web_search"))
    web_search_reason = classification_dict.get("web_search_reason")

    context_update = _orchestrated_collect_context_node(
        state,
        on_before_web_search=status_tracker.hook(
            stage="thinking",
            label=LABEL_WEB_SEARCH,
            reason_code="web_search_started",
        ),
        on_web_search_retry=status_tracker.hook(
            stage="thinking",
            label=LABEL_WEB_SEARCH_RETRY,
            reason_code="web_search_retry_sources",
        ),
        on_web_search_weak_context=(
            status_tracker.hook(
                stage="thinking",
                label=LABEL_WEB_SEARCH_WEAK,
                reason_code="web_search_weak_context",
            )
            if need_web_search
            else None
        ),
    )
    state.update(context_update)

    for event in status_tracker.pending_events:
        yield event
    status_tracker.pending_events.clear()

    classification_dict = (
        state.get("classification") or _ORCHESTRATED_FALLBACK_CLASSIFICATION.copy()
    )
    subject: str = classification_dict.get("subject", "general")
    intent: str = classification_dict.get("intent", "explain")
    difficulty: str = classification_dict.get("difficulty", "default")
    context_text: str = state.get("context_text") or ""

    generating_event = _emit_status(
        stage="generating", intent=intent, reason_code="generating"
    )
    if generating_event is not None:
        yield generating_event

    chunk_count = 0
    generator_fallback_emitted = False
    try:
        for chunk in adapter.generate_stream(
            request_id=request_id,
            query=query,
            subject=subject,
            intent=intent,
            difficulty=difficulty,
            context_text=context_text,
            web_search_reason=str(web_search_reason) if web_search_reason else None,
            on_before_generator_fallback=status_tracker.hook(
                stage="generating",
                label=LABEL_GENERATOR_FALLBACK,
                reason_code="generator_fallback",
            ),
            on_before_continuation=status_tracker.hook(
                stage="generating",
                label=LABEL_ANSWER_CONTINUATION,
                reason_code="answer_continuation",
            ),
        ):
            if not generator_fallback_emitted and status_tracker.pending_events:
                for event in status_tracker.pending_events:
                    yield event
                status_tracker.pending_events.clear()
                generator_fallback_emitted = True

            chunk_count += 1
            if not first_chunk_logged:
                first_chunk_logged = True
                logger.info(
                    "streaming_doubt_solver  request_id=%s  first_chunk_emitted=true",
                    request_id,
                )
            yield DoubtSolverStreamEvent(
                type="chunk",
                request_id=request_id,
                content=chunk,
            )
    except Exception as exc:
        logger.warning(
            "streaming_doubt_solver  stream_error  request_id=%s  stage=generating  "
            "error_type=%s",
            request_id,
            type(exc).__name__,
        )
        yield DoubtSolverStreamEvent(
            type="error",
            request_id=request_id,
            stage="error",
            label=get_stream_label("error"),
        )
        return

    finalizing_event = _emit_status(stage="finalizing", reason_code="finalizing")
    if finalizing_event is not None:
        yield finalizing_event

    latency_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "streaming_doubt_solver  request_id=%s  stream_completed=true  "
        "stage=complete  chunk_count=%d  latency_ms=%d",
        request_id,
        chunk_count,
        latency_ms,
    )

    yield DoubtSolverStreamEvent(
        type="complete",
        request_id=request_id,
        stage="complete",
        label=get_stream_label("complete"),
        metadata={"request_id": request_id},
    )
