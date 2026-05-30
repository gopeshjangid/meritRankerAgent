"""
app/schemas/doubt_solver.py
---------------------------
Pydantic v2 schemas for the Doubt Solver workflow.

Models:
    DoubtSolverRequest      — inbound payload (validated at API boundary)
    QueryClassification     — classifier output (validated at service boundary)
    AnswerOutput            — answer generator output (validated at service boundary)
    DoubtSolverResponse     — outbound payload
    DoubtSolverState        — Python-layer state (Pydantic); the LangGraph
                              internal TypedDict lives in doubt_solver_graph.py
    DoubtSolverClassification — lean classification for the orchestrated graph state
                              (ENABLE_ORCHESTRATED_DOUBT_SOLVER path only)
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DoubtSolverRequest(BaseModel):
    """Validated inbound payload for a doubt solver request."""

    mode: Literal["doubt_solver"]
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The student's question or doubt.",
    )
    user_id: str = Field(
        default="local-user",
        min_length=1,
        max_length=128,
        description="Caller identifier — used for tracing.",
    )
    language: Literal["en", "hi", "hinglish"] = Field(
        default="en",
        description="Preferred response language.",
    )
    stream: bool = Field(
        default=False,
        description="Request a streaming response with student-friendly status "
                    "labels and real answer chunks. Only honoured by the "
                    "orchestrated graph path.",
    )

    model_config = {"str_strip_whitespace": True}


class QueryClassification(BaseModel):
    """Structured output from the query classifier service."""

    intent: Literal[
        "solve_question",
        "explain_concept",
        "explain_option",
        "general_doubt",
        "practice_question",
        "visualize_question",
        "unknown",
    ] = Field(description="Detected intent of the student query.")
    subject: str = Field(
        default="unknown",
        description="Detected subject area (e.g. 'math', 'reasoning').",
    )
    topic: str | None = Field(
        default=None,
        description="Detected topic within the subject, if identifiable.",
    )
    response_style: Literal["step_by_step", "short_answer", "simple_explanation"] = Field(
        default="step_by_step",
        description="Preferred response style for this intent.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score.",
    )
    difficulty: Literal["default", "basic", "intermediate", "advanced"] = Field(
        default="default",
        description="Detected difficulty level of the query.",
    )
    retrieval_need: Literal["none", "concept_context", "similar_question", "unknown"] = Field(
        default="unknown",
        description="Whether retrieval context would improve the answer.",
    )
    classification_source: Literal["deterministic", "llm", "fallback"] = Field(
        default="deterministic",
        description="Which path produced this classification.",
    )
    reasoning_summary: str | None = Field(
        default=None,
        max_length=500,
        description="Short non-sensitive explanation of the classification (from LLM only).",
    )


class AnswerOutput(BaseModel):
    """Validated output from the answer generator service.

    Carries the answer content, the path that produced it, and a truncation
    flag.  Validated at the service boundary before being written to graph state.
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The generated answer text.",
    )
    answer_source: Literal["mock", "llm", "fallback"] = Field(
        description="Which path produced this answer.",
    )
    is_truncated: bool = Field(
        default=False,
        description="True when model output exceeded the max length and was truncated.",
    )


class DoubtSolverResponse(BaseModel):
    """Serialised outbound payload for a doubt solver response."""

    success: bool = Field(description="True when an answer was produced.")
    request_id: str = Field(description="UUID assigned at the entrypoint.")
    mode: Literal["doubt_solver"]
    answer: str = Field(description="The generated explanation.")
    classification: QueryClassification = Field(
        description="Classification result from the classifier node."
    )
    needs_review: bool = Field(
        default=False,
        description="True when the answer requires human review (e.g. low confidence).",
    )
    answer_source: Literal["mock", "llm", "fallback"] = Field(
        default="mock",
        description="Which path produced the answer.",
    )
    is_truncated: bool = Field(
        default=False,
        description="True when the generated answer was truncated to fit the max length.",
    )
    used_retrieval: bool = Field(
        default=False,
        description="True when KB retrieval was called and returned at least one result.",
    )
    source_count: int = Field(
        default=0,
        ge=0,
        description="Number of context sources (KB results + DynamoDB records) used.",
    )
    context_used: bool = Field(
        default=False,
        description="True when retrieved context was included in the answer generation prompt.",
    )


class DoubtSolverState(BaseModel):
    """Python-layer state for the Doubt Solver workflow.

    Used outside the LangGraph graph (e.g. in main.py) to package request
    context as a typed object.  The actual LangGraph internal state uses a
    plain TypedDict (DoubtSolverGraphState in doubt_solver_graph.py) so that
    LangGraph's reducer system can serialise it freely.
    """

    request: DoubtSolverRequest = Field(description="The validated inbound request.")
    request_id: str = Field(description="UUID assigned at the entrypoint.")
    classification: QueryClassification | None = Field(
        default=None,
        description="Classifier output, populated after classify_query node.",
    )
    answer: str | None = Field(
        default=None,
        description="Generated answer string, populated after generate_answer node.",
    )
    response: DoubtSolverResponse | None = Field(
        default=None,
        description="Final structured response, populated after build_response node.",
    )


# ---------------------------------------------------------------------------
# DoubtSolverClassification — lean classification for the orchestrated graph
# (ENABLE_ORCHESTRATED_DOUBT_SOLVER path only)
# ---------------------------------------------------------------------------


class DoubtSolverClassification(BaseModel):
    """Minimal classification for the orchestrated Doubt Solver graph state.

    Intentionally small — only what the generator node needs to build a
    RouteRequest.  Internal classifier scores, topics, and style hints stay
    outside the orchestrated graph state.

    Allowed values match the route config in llm_routes.yaml:
        subject:    math | reasoning | english | general
        intent:     solve | explain | practice
        difficulty: default | basic | intermediate | advanced
        retrieval_required: True when the classifier recommends context retrieval
    """

    subject: str = Field(default="general")
    intent: str = Field(default="explain")
    difficulty: str = Field(default="default")
    retrieval_required: bool = Field(default=False)

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# DoubtSolverStreamEvent — single event in a streaming orchestrated response
# ---------------------------------------------------------------------------


_FORBIDDEN_STREAM_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "prompt",
        "system_prompt",
        "user_prompt",
        "messages",
        "context",
        "context_text",
        "query",
        "api_key",
        "secret",
        "credential",
        "authorization",
        "raw_response",
        "provider",
        "deployment",
        "model_id",
        "stack_trace",
    }
)


class DoubtSolverStreamEvent(BaseModel):
    """A single event in an orchestrated Doubt Solver streaming response.

    Events are emitted in order:
        1. ``status``   — student-friendly progress labels (understanding, thinking, …).
        2. ``chunk``    — zero or more, each carries one text chunk of the answer.
        3. ``complete`` — exactly one, last event, may carry safe metadata.
        4. ``error``    — replaces ``complete`` when generation fails.

    Security note: ``content`` must contain ONLY answer text chunks.
    No prompt, messages, context, API keys, or provider details may appear
    in any field.
    """

    type: Literal["status", "chunk", "complete", "error"] = Field(
        description="Type of streaming event.",
    )
    request_id: str = Field(
        min_length=1,
        description="UUID of the originating request.",
    )
    stage: str | None = Field(
        default=None,
        description="Internal stage name (status/complete/error events only).",
    )
    label: str | None = Field(
        default=None,
        description="Student-facing label (status/complete/error events only).",
    )
    content: str | None = Field(
        default=None,
        description=(
            "Answer text chunk (non-None only for 'chunk' events). "
            "Must contain answer text only — no prompt, context, or credentials."
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Safe tracing metadata only (e.g. request_id echo). "
            "Must not contain secrets, prompt text, context, or provider details."
        ),
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_event_shape(self) -> DoubtSolverStreamEvent:
        if self.type == "chunk":
            if self.content is None:
                raise ValueError("chunk event must have content")
        elif self.type == "status":
            if not self.stage or not self.label:
                raise ValueError("status event must have stage and label")
        elif self.type == "error":
            if not self.label:
                raise ValueError("error event must have a safe label/message")
        elif self.type == "complete":
            pass

        for key in self.metadata:
            if key.lower() in _FORBIDDEN_STREAM_METADATA_KEYS:
                raise ValueError(
                    f"metadata must not contain forbidden key: {key!r}"
                )

        return self
