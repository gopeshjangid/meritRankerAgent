"""Minimal internal SolutionBrief schema for generator context."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SolutionBrief(BaseModel):
    """Compact structured brief — internal only, never graph state."""

    subject: str = Field(default="", max_length=64)
    topic: str = Field(default="", max_length=128)
    given: list[str] = Field(default_factory=list, max_length=7)
    find: str = Field(default="", max_length=512)
    context: list[str] = Field(default_factory=list, max_length=7)
    core_concepts: list[str] = Field(default_factory=list, max_length=7)
    solution_approach: list[str] = Field(default_factory=list, max_length=7)
    risk_flags: list[str] = Field(default_factory=list, max_length=7)
    generator_instructions: list[str] = Field(default_factory=list, max_length=7)

    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    @field_validator(
        "given",
        "context",
        "core_concepts",
        "solution_approach",
        "risk_flags",
        "generator_instructions",
        mode="before",
    )
    @classmethod
    def _cap_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:7]
