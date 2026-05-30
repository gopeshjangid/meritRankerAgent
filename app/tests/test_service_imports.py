"""
tests/test_service_imports.py
------------------------------
Import-boundary guard tests: verify that compat wrappers under the old
service paths remain thin public re-export shims and do not contain
private forwarding logic.

Covers:
    - No compat wrapper under services/llm_orchestration/ or services/llm_providers/
      contains a __getattr__ module-level function.
    - No .py file other than services/llm/orchestration/config_registry.py accesses
      the private _registry singleton directly.
    - Canonical service paths import without side effects.
    - No frontend artifacts under app/.
    - Orchestrated doubt solver modules do not import legacy model_router.

[NOT VERIFIED]: checks are substring-based, not AST-based.  A reference inside
a multi-line string literal would be a false positive — reviewed manually.
"""

from __future__ import annotations

import importlib
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1]  # app/

_COMPAT_DIRS = [
    _APP_DIR / "services" / "llm_orchestration",
    _APP_DIR / "services" / "llm_providers",
]

# Canonical module that is allowed to contain _registry.
_REGISTRY_MODULE = (
    _APP_DIR / "services" / "llm" / "orchestration" / "config_registry.py"
).resolve()

_EXCLUDE_DIRS = {".venv", "__pycache__"}

_ORCHESTRATED_MODULES = [
    "services.doubt_solver.answer_generation_adapter",
    "services.doubt_solver.streaming_doubt_solver_service",
    "services.llm.orchestration.orchestrator",
    "services.llm.orchestration.model_execution",
]

_CANONICAL_IMPORTS = [
    "services.doubt_solver.answer_generation_adapter",
    "services.doubt_solver.streaming_doubt_solver_service",
    "services.doubt_solver.stream_labels",
    "services.llm.orchestration.orchestrator",
    "services.llm.orchestration.config_registry",
    "services.llm.providers.provider_factory",
    "services.secrets.provider_credentials",
    "services.context_retrieval",
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compat_wrappers_contain_no_getattr() -> None:
    """Compat shims under llm_orchestration/ and llm_providers/ must not contain
    __getattr__ (private forwarding).  Only public *-imports are allowed."""
    violations: list[str] = []

    for compat_dir in _COMPAT_DIRS:
        if not compat_dir.exists():
            continue
        for path in compat_dir.rglob("*.py"):
            if any(excl in path.parts for excl in _EXCLUDE_DIRS):
                continue
            text = path.read_text()
            if "__getattr__" in text:
                rel = path.relative_to(_APP_DIR)
                violations.append(
                    f"  {rel}: __getattr__ found — compat wrappers must be thin re-exports"
                )

    assert not violations, (
        "Private __getattr__ forwarding found in compat wrappers:\n"
        + "\n".join(violations)
    )


def test_compat_wrappers_are_reexport_only() -> None:
    """Each compat wrapper .py file must contain only comments and a star-import."""
    violations: list[str] = []

    for compat_dir in _COMPAT_DIRS:
        if not compat_dir.exists():
            continue
        for path in compat_dir.rglob("*.py"):
            if any(excl in path.parts for excl in _EXCLUDE_DIRS):
                continue
            code_lines = [
                line.strip()
                for line in path.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if len(code_lines) != 1 or "import *" not in code_lines[0]:
                rel = path.relative_to(_APP_DIR)
                violations.append(f"  {rel}: expected single star-import, got {code_lines!r}")

    assert not violations, (
        "Compat wrappers must be thin re-exports only:\n" + "\n".join(violations)
    )


def test_no_private_registry_access_outside_canonical_module() -> None:
    """No .py file may access the module-level _registry singleton via dot-access
    on a config_registry import (e.g. ``config_registry._registry``).

    Tests and app code must use get_registry() / reset_registry() (public API).
    The canonical module itself (config_registry.py) is exempt.
    """
    violations: list[str] = []

    # Pattern: any identifier followed by ._registry (module attribute access).
    # This catches: config_registry._registry, _target._registry, mod._registry
    import re

    _DOT_REGISTRY_RE = re.compile(r"\w+\._registry\b")

    for path in (_APP_DIR).rglob("*.py"):
        if any(excl in path.parts for excl in _EXCLUDE_DIRS):
            continue
        if path.resolve() == _REGISTRY_MODULE:
            continue  # canonical module — allowed
        if path.resolve() == Path(__file__).resolve():
            continue

        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _DOT_REGISTRY_RE.search(line):
                # Instance/class attribute access is fine (self._registry, cls._registry).
                if "self._registry" in line or "cls._registry" in line:
                    continue
                rel = path.relative_to(_APP_DIR)
                violations.append(
                    f"  {rel}:{lineno}: private _registry dot-access  →  {line.rstrip()}"
                )

    assert not violations, (
        "Private _registry dot-access found outside canonical module "
        "(use get_registry() / reset_registry() instead):\n"
        + "\n".join(violations)
    )


def test_canonical_service_imports_succeed() -> None:
    """Canonical service paths import without error."""
    for module_name in _CANONICAL_IMPORTS:
        importlib.import_module(module_name)


def test_no_frontend_artifacts_under_app() -> None:
    """No TypeScript/React UI files under app/."""
    frontend_suffixes = {".ts", ".tsx", ".jsx", ".css"}
    violations: list[str] = []

    for path in _APP_DIR.rglob("*"):
        if any(excl in path.parts for excl in _EXCLUDE_DIRS):
            continue
        if path.suffix.lower() in frontend_suffixes:
            violations.append(f"  {path.relative_to(_APP_DIR)}")

    assert not violations, (
        "Frontend artifacts found under app/:\n" + "\n".join(violations)
    )


def test_orchestrated_modules_do_not_import_model_router() -> None:
    """Orchestrated path modules must not import legacy model_router."""
    violations: list[str] = []

    for module_name in _ORCHESTRATED_MODULES:
        module = importlib.import_module(module_name)
        source_path = Path(module.__file__).resolve()
        for lineno, line in enumerate(source_path.read_text().splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "model_router" not in stripped or "import" not in stripped:
                continue
            rel = source_path.relative_to(_APP_DIR)
            violations.append(f"  {rel}:{lineno}: {stripped}")

    assert not violations, (
        "Orchestrated modules must not import legacy model_router:\n"
        + "\n".join(violations)
    )
