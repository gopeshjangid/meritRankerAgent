"""
app/schemas/state.py
---------------------
Pydantic v2 model representing the data carried through the LangGraph workflow.

Design note:
    AgentState is the Python-layer view of the graph's data.  The actual
    LangGraph internal state uses a TypedDict (defined in demo_graph.py)
    because LangGraph's reducer system works most reliably with plain dicts.
    main.py converts AgentState ↔ graph dict at the boundary.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.request import AgentRequest


class AgentState(BaseModel):
    """Mutable state object passed into and returned from the agent graph."""

    request: AgentRequest = Field(..., description="The validated incoming request.")
    request_id: str = Field(..., description="UUID for this invocation, set in main.py.")
    answer: str | None = Field(
        default=None,
        description="The answer produced by the graph.  None until respond_node runs.",
    )
