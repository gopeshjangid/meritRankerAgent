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
    _orchestrated_classify_node,
    _orchestrated_collect_context_node,
)
from schemas.doubt_solver import DoubtSolverStreamEvent
from services.doubt_solver.answer_generation_adapter import AnswerGenerationAdapter
from services.doubt_solver.stream_labels import get_stream_label

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
) -> DoubtSolverStreamEvent:
    return DoubtSolverStreamEvent(
        type="status",
        request_id=request_id,
        stage=stage,
        label=get_stream_label(stage, intent),
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

    logger.info(
        "streaming_doubt_solver  request_id=%s  stream_started=true",
        request_id,
    )

    def _emit_status(*, stage: str, intent: str | None = None) -> DoubtSolverStreamEvent:
        logger.info(
            "streaming_doubt_solver  request_id=%s  status_emitted  stage=%s",
            request_id,
            stage,
        )
        return _status_event(request_id=request_id, stage=stage, intent=intent)

    yield _emit_status(stage="understanding")

    state = {
        "request_id": request_id,
        "query": query,
        "classification": None,
        "context_text": "",
        "answer": None,
    }

    classify_update = _orchestrated_classify_node(state)
    state.update(classify_update)

    yield _emit_status(stage="thinking")

    context_update = _orchestrated_collect_context_node(state)
    state.update(context_update)

    classification_dict = (
        state.get("classification") or _ORCHESTRATED_FALLBACK_CLASSIFICATION.copy()
    )
    subject: str = classification_dict.get("subject", "general")
    intent: str = classification_dict.get("intent", "explain")
    difficulty: str = classification_dict.get("difficulty", "default")
    context_text: str = state.get("context_text") or ""

    yield _emit_status(stage="generating", intent=intent)

    chunk_count = 0
    try:
        for chunk in adapter.generate_stream(
            request_id=request_id,
            query=query,
            subject=subject,
            intent=intent,
            difficulty=difficulty,
            context_text=context_text,
        ):
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

    yield _emit_status(stage="finalizing")

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
