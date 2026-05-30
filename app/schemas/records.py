"""
app/schemas/records.py
-----------------------
Lightweight Pydantic v2 schemas for DynamoDB question and pattern records.

[NOT VERIFIED] The real DynamoDB table schema is not finalised.  These models
represent the minimum expected shape.  Additional attributes come through in the
``metadata`` dict and are not validated.

These schemas are provided for consumers who want to validate a fetched record.
The domain service (question_record_service) returns plain ``dict`` — use
these models for validation at the call site when the schema is confirmed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QuestionRecord(BaseModel):
    """Minimal schema for a fetched question record.

    [NOT VERIFIED] Real table attribute names and required fields.
    [ASSUMPTION] ``question_id`` is the primary key attribute.
    """

    question_id: str
    text: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatternRecord(BaseModel):
    """Minimal schema for a fetched pattern record.

    [NOT VERIFIED] Real table attribute names and required fields.
    [ASSUMPTION] ``pattern_id`` is the primary key attribute.
    """

    pattern_id: str
    title: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
