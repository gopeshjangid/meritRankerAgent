"""Future LLM planner/refiner policy — not invoked in this patch."""

from __future__ import annotations

from services.context_retrieval.context_models import ContextRetrievalRequest
from services.solution_brief.models import SolutionBrief

# Minimal schema fields an future LLM planner may populate (same as SolutionBrief).
PLANNER_BRIEF_FIELDS: frozenset[str] = frozenset(SolutionBrief.model_fields.keys())


def should_run_llm_planner(
    request: ContextRetrievalRequest,
    *,
    kb_item_count: int = 0,
    web_item_count: int = 0,
    conflicting_web_sources: bool = False,
    image_ocr_confidence: str | None = None,
) -> bool:
    """Return True only when a future conditional LLM planner should run.

    This patch never calls an LLM planner — the function documents policy and
    supports tests confirming planner stays off by default.
    """
    _ = (
        request,
        kb_item_count,
        web_item_count,
        conflicting_web_sources,
        image_ocr_confidence,
    )
    return False
