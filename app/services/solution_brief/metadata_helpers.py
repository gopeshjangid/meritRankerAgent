"""Safe metadata extraction helpers for SolutionBrief and KB fallback context."""

from __future__ import annotations

import re
from typing import Any

_SUBJECT_LABELS: dict[str, str] = {
    "math": "Math",
    "reasoning": "Reasoning",
    "english": "English",
    "general": "General Studies",
}


def safe_str(value: Any, *, max_length: int | None = None) -> str:
    """Coerce a metadata value to a trimmed string; dicts are skipped."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, (bool, int, float)):
        text = str(value).strip()
    elif isinstance(value, (list, tuple, set)):
        return safe_join(value, max_length=max_length)
    elif isinstance(value, dict):
        return ""
    else:
        text = str(value).strip()
    if max_length is not None and len(text) > max_length:
        return text[:max_length].rstrip()
    return text


def safe_list(value: Any, *, max_items: int = 7, item_max_length: int = 160) -> list[str]:
    """Normalize metadata to a deduped list of short strings."""
    if value is None:
        return []
    items: list[str] = []
    if isinstance(value, str):
        raw_items = re.split(r"[,;|\n]", value)
        items = [part.strip(" -•") for part in raw_items if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        for entry in value:
            if entry is None:
                continue
            if isinstance(entry, dict):
                continue
            text = safe_str(entry, max_length=item_max_length)
            if text:
                items.append(text)
    elif isinstance(value, dict):
        return []
    else:
        text = safe_str(value, max_length=item_max_length)
        if text:
            items = [text]

    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if not item or key in seen:
            continue
        seen.add(key)
        result.append(item[:item_max_length])
        if len(result) >= max_items:
            break
    return result


def safe_join(value: Any, *, separator: str = ", ", max_length: int | None = None) -> str:
    """Join list-like metadata into one compact string."""
    items = safe_list(value)
    if not items:
        return ""
    joined = separator.join(items)
    if max_length is not None and len(joined) > max_length:
        return joined[:max_length].rstrip()
    return joined


def normalize_metadata_key(metadata: dict[str, Any], candidate_keys: tuple[str, ...]) -> Any:
    """Return the first present, non-empty metadata value for candidate keys."""
    for key in candidate_keys:
        if key not in metadata:
            continue
        value = metadata[key]
        if value is None or value == "":
            continue
        return value
    return None


def subject_label(subject: str) -> str:
    """Map classifier subject to a compact display label."""
    return _SUBJECT_LABELS.get(subject.lower(), subject.title() or "General")


def humanize_token(value: str, *, max_length: int = 128) -> str:
    """Humanize a pattern/topic token for generator-facing text."""
    cleaned = safe_str(value, max_length=max_length)
    if not cleaned:
        return ""
    cleaned = cleaned.replace("_", " ").replace("-", " ").strip()
    if cleaned.isupper():
        return cleaned.title()[:max_length]
    return cleaned[:max_length]
