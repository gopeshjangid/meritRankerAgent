"""
app/schemas/retrieval.py
------------------------
Pydantic v2 schemas for Bedrock Knowledge Base retrieval results.

These models are used exclusively by bedrock_kb_service and its tests.
They are NOT part of the external API schema (DoubtSolverRequest / Response).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class KnowledgeBaseResult(BaseModel):
    """A single retrieved chunk from the Bedrock Knowledge Base."""

    content: str = Field(..., min_length=1, max_length=8000)
    score: float | None = Field(default=None, ge=0)
    source_id: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)
    record_ids: list[str] = Field(default_factory=list, max_length=20)


class RetrievalResponse(BaseModel):
    """Aggregated response from a KB retrieval call."""

    query: str
    results: list[KnowledgeBaseResult]
    result_count: int
    retrieval_source: Literal["disabled", "bedrock_kb", "fallback"] = "disabled"
