"""
app/schemas/request.py
-----------------------
Pydantic v2 model for incoming agent requests.

All validation happens here so the rest of the code can trust the types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Validated inbound payload from a caller."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The user message or task description.",
    )
    user_id: str = Field(
        default="local-user",
        min_length=1,
        max_length=128,
        description="Caller identifier — used for tracing and future personalisation.",
    )
    mode: str = Field(
        default="demo",
        min_length=1,
        max_length=64,
        description="Execution mode.  Use 'demo' for local testing.",
    )

    model_config = {"str_strip_whitespace": True}
