"""
app/schemas/streaming.py
------------------------
Provider-neutral Pydantic v2 schemas for the streaming adapter layer.

StreamEvent is the single stable event shape emitted by streaming_adapter.py.
All streaming code in this project MUST use these schemas as its public contract.

Schema changes here are a public contract — do not rename or remove fields without
updating streaming_adapter.py, its tests, and the feature docs.

[NOT VERIFIED] AgentCore HTTP streaming support is not verified in this release.
               These schemas are the foundation for future wiring.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """A single event in a streaming response.

    Events are emitted in order::

        1. ``metadata`` — exactly one, first event, carries request_id + context.
        2. ``content_delta`` — zero or more, each carries one text chunk.
        3. ``final`` — exactly one, last event, is_final=True.
        4. ``error`` — replaces ``final`` when an error occurs mid-stream.

    The ``content_delta`` field is the empty string for ``metadata``, ``final``,
    and ``error`` events.  Callers should only append ``content_delta`` to their
    buffer when ``event_type == "content_delta"``.

    Security note: ``metadata`` MUST NOT contain secrets, API keys, or full
    provider config.  Only safe tracing fields (request_id, source, model_label)
    are allowed.
    """

    event_type: Literal["metadata", "content_delta", "final", "error"] = Field(
        description="Type of streaming event.",
    )
    request_id: str = Field(
        min_length=1,
        description="UUID of the originating request — used for correlation.",
    )
    content_delta: str = Field(
        default="",
        description="Incremental text to append. Non-empty only for content_delta events.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe tracing metadata (request_id, source, model_label). No secrets.",
    )
    is_final: bool = Field(
        default=False,
        description="True only on the final or error event.",
    )
