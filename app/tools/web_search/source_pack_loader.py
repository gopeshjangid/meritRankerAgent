"""Load and validate web search source packs from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PACKS_FILE = Path(__file__).parent / "source_packs.yaml"
_DEFAULT_PACK_NAME = "current_affairs_india"


@dataclass(frozen=True)
class SourcePack:
    """One named source policy pack."""

    name: str
    topic: str
    trusted_domains: tuple[str, ...]
    reputed_domains: tuple[str, ...]
    exam_prep_domains: tuple[str, ...]
    blocked_domains: tuple[str, ...]


@dataclass(frozen=True)
class SourcePackCatalog:
    """Validated source pack catalog."""

    global_blocked: tuple[str, ...]
    packs: dict[str, SourcePack]

    def get_pack(self, name: str) -> SourcePack:
        if name in self.packs:
            return self.packs[name]
        if _DEFAULT_PACK_NAME in self.packs:
            return self.packs[_DEFAULT_PACK_NAME]
        return SourcePack(
            name="default",
            topic="news",
            trusted_domains=(),
            reputed_domains=(),
            exam_prep_domains=(),
            blocked_domains=(),
        )


def _normalize_domains(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    domains: list[str] = []
    for entry in raw:
        text = str(entry).strip().lower().removeprefix("www.")
        if text:
            domains.append(text)
    return tuple(domains)


def _parse_pack(name: str, raw: dict[str, Any]) -> SourcePack:
    topic = str(raw.get("topic") or "general").strip().lower()
    return SourcePack(
        name=name,
        topic=topic,
        trusted_domains=_normalize_domains(raw.get("trusted_domains")),
        reputed_domains=_normalize_domains(raw.get("reputed_domains")),
        exam_prep_domains=_normalize_domains(raw.get("exam_prep_domains")),
        blocked_domains=_normalize_domains(raw.get("blocked_domains")),
    )


def load_source_pack_catalog(path: Path | None = None) -> SourcePackCatalog:
    """Load source packs from YAML and validate required shape."""
    pack_path = path or _PACKS_FILE
    with pack_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError("source_packs.yaml must be a mapping")

    global_blocked_raw = raw.get("global_blocked") or {}
    global_blocked = _normalize_domains(
        global_blocked_raw.get("domains") if isinstance(global_blocked_raw, dict) else []
    )

    packs_raw = raw.get("packs") or {}
    if not isinstance(packs_raw, dict):
        raise ValueError("source_packs.packs must be a mapping")

    packs: dict[str, SourcePack] = {}
    for name, pack_raw in packs_raw.items():
        if not isinstance(pack_raw, dict):
            continue
        packs[str(name)] = _parse_pack(str(name), pack_raw)

    return SourcePackCatalog(global_blocked=global_blocked, packs=packs)


@lru_cache(maxsize=1)
def get_source_pack_catalog() -> SourcePackCatalog:
    """Return cached source pack catalog."""
    return load_source_pack_catalog()
