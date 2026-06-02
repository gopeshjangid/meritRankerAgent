"""Strict JSON parsing for classifier LLM output."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_PATTERN = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class ClassifierJsonError(ValueError):
    """Classifier output is not a single strict JSON object."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def _strip_outer_whitespace(text: str) -> str:
    return text.strip()


def _try_unfence(text: str) -> tuple[str, bool]:
    match = _FENCE_PATTERN.match(text)
    if match:
        return match.group(1).strip(), True
    return text, False


def parse_classifier_json_strict(content: str) -> tuple[dict[str, Any], bool]:
    """Parse exactly one JSON object; reject trailing text and multiple objects.

    Returns:
        (parsed_dict, recovered_from_fence)

    Raises:
        ClassifierJsonError: On empty input, invalid JSON, extra trailing text,
            or multiple JSON values.
    """
    if not content or not content.strip():
        raise ClassifierJsonError("empty_output", "Classifier output is empty.")

    stripped = _strip_outer_whitespace(content)
    unfenced, recovered = _try_unfence(stripped)
    if recovered:
        stripped = unfenced

    decoder = json.JSONDecoder()
    try:
        parsed, end_idx = decoder.raw_decode(stripped)
    except json.JSONDecodeError as exc:
        raise ClassifierJsonError(
            "json_decode_error",
            f"Classifier JSON decode failed: {exc.msg}",
        ) from exc

    trailing = stripped[end_idx:].strip()
    if trailing:
        raise ClassifierJsonError(
            "extra_trailing_text",
            "Classifier output contains text after the JSON object.",
        )

    if not isinstance(parsed, dict):
        raise ClassifierJsonError(
            "not_object",
            "Classifier output must be a single JSON object.",
        )

    return parsed, recovered
