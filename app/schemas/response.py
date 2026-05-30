"""
app/schemas/response.py
------------------------
Pydantic v2 model for outgoing agent responses.

Keeping request and response in separate modules makes it easy to evolve
each independently (e.g. versioned response shapes, new fields).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Standardised outbound payload returned to the caller."""

    success: bool = Field(..., description="True when the agent completed without error.")
    answer: str = Field(..., description="The agent's textual response or error message.")
    request_id: str = Field(..., description="UUID generated per request for tracing.")
    mode: str = Field(default="demo", description="Echoes the mode from the request.")
