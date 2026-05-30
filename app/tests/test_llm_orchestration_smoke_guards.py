"""
app/tests/test_llm_orchestration_smoke_guards.py
-------------------------------------------------
Guard tests for ``app/scripts/smoke_llm_orchestration.py`` — Part 7.

These tests verify the smoke script's safety properties without ever running
real provider calls.  The smoke script is a manual opt-in tool; these tests
prove it behaves safely when the opt-in flag is absent or incorrect.

Test coverage:
1.  Smoke script exits 0 when RUN_REAL_LLM_SMOKE is not set.
2.  Smoke script exits 0 when RUN_REAL_LLM_SMOKE=false.
3.  Smoke script exits 0 when RUN_REAL_LLM_SMOKE is empty string.
4.  No provider client is instantiated when flag is missing.
5.  Smoke script is NOT in the tests/ directory (not auto-collected by pytest).
6.  Smoke script file exists in the expected scripts/ location.
7.  Smoke script is documented as manual-only (docstring present).
8.  Smoke script does not print env secret values even when invoked.
9.  Smoke script requires a valid --provider value (rejects unknown provider).
10. Smoke script --provider is restricted to the SUPPORTED_PROVIDERS set.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_APP_DIR = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _APP_DIR / "scripts"
_SMOKE_SCRIPT = _SCRIPTS_DIR / "smoke_llm_orchestration.py"


# ---------------------------------------------------------------------------
# Test 1 — exits 0 when RUN_REAL_LLM_SMOKE is not set at all
# ---------------------------------------------------------------------------


def test_smoke_exits_0_when_flag_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running the smoke script without the flag must exit with code 0 (no-op)."""
    env = {k: v for k, v in os.environ.items() if k != "RUN_REAL_LLM_SMOKE"}
    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
    )
    assert result.returncode == 0, (
        f"Expected exit 0 when flag not set. Got: {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "RUN_REAL_LLM_SMOKE" in result.stdout, (
        "Output should mention RUN_REAL_LLM_SMOKE when flag is absent"
    )


# ---------------------------------------------------------------------------
# Test 2 — exits 0 when RUN_REAL_LLM_SMOKE=false
# ---------------------------------------------------------------------------


def test_smoke_exits_0_when_flag_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {**os.environ, "RUN_REAL_LLM_SMOKE": "false"}
    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Test 3 — exits 0 when RUN_REAL_LLM_SMOKE is empty string
# ---------------------------------------------------------------------------


def test_smoke_exits_0_when_flag_is_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {**os.environ, "RUN_REAL_LLM_SMOKE": ""}
    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Test 4 — no provider client instantiation when flag is missing
# ---------------------------------------------------------------------------


def test_smoke_does_not_instantiate_providers_without_flag() -> None:
    """When RUN_REAL_LLM_SMOKE is not true, no provider SDKs should be touched.

    We verify this by checking that the subprocess exits with code 0 (no-op)
    and that no credential reads or SDK imports caused an error.
    """
    env = {k: v for k, v in os.environ.items() if k != "RUN_REAL_LLM_SMOKE"}
    # Remove all provider credentials too — if any are read, the script would fail.
    for cred_var in (
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
    ):
        env.pop(cred_var, None)

    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
    )
    # Must exit cleanly — no provider errors, no credential errors.
    assert result.returncode == 0
    # Must not have printed any error about missing credentials.
    assert "SecretNotFoundError" not in result.stderr
    assert "OPENAI_API_KEY" not in result.stderr
    assert "AZURE_OPENAI_API_KEY" not in result.stderr


# ---------------------------------------------------------------------------
# Test 5 — smoke script is NOT in tests/ directory
# ---------------------------------------------------------------------------


def test_smoke_script_not_in_tests_directory() -> None:
    """Smoke script must live under scripts/, not tests/.

    If it were in tests/, pytest would auto-collect it and try to run it as
    a test module on every ``make check``, which would trigger the opt-in
    flag check.
    """
    tests_dir = Path(__file__).resolve().parent
    assert not (tests_dir / "smoke_llm_orchestration.py").exists(), (
        "smoke_llm_orchestration.py must NOT be in tests/. Found in tests/."
    )


# ---------------------------------------------------------------------------
# Test 6 — smoke script exists in the expected scripts/ location
# ---------------------------------------------------------------------------


def test_smoke_script_exists_in_scripts_directory() -> None:
    assert _SMOKE_SCRIPT.exists(), (
        f"Smoke script not found at expected location: {_SMOKE_SCRIPT}"
    )
    assert _SMOKE_SCRIPT.is_file()


# ---------------------------------------------------------------------------
# Test 7 — smoke script is documented as manual-only
# ---------------------------------------------------------------------------


def test_smoke_script_has_manual_only_documentation() -> None:
    """Smoke script must have a docstring or comment clearly stating it is
    manual-only and NOT run by make check / pytest."""
    content = _SMOKE_SCRIPT.read_text()
    # Check for key terms that document the manual-only nature.
    assert "NOT run" in content or "not run" in content.lower() or "manual" in content.lower(), (
        "Smoke script must document that it is NOT run by make check / pytest."
    )
    assert "RUN_REAL_LLM_SMOKE" in content, (
        "Smoke script must document the RUN_REAL_LLM_SMOKE flag."
    )


# ---------------------------------------------------------------------------
# Test 8 — smoke script does not print env secret values in its output
# ---------------------------------------------------------------------------


def test_smoke_no_secret_values_in_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the flag is set but provider credentials are missing, the script
    should fail with a clean error and NOT echo any secret values to stdout.

    We set a fake API key and verify it does not appear in stdout.
    """
    env = {
        **os.environ,
        "RUN_REAL_LLM_SMOKE": "true",
        "OPENAI_API_KEY": "sk-test-fakekeyvalue123",
    }
    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT), "--provider", "openai"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
        timeout=10,  # short timeout — should fail fast without real API
    )
    # The script may fail (network error / auth error) — that's expected.
    # What matters is the fake API key value NEVER appears in stdout or stderr.
    assert "sk-test-fakekeyvalue123" not in result.stdout, (
        "Smoke script must NEVER echo API key values to stdout"
    )
    assert "sk-test-fakekeyvalue123" not in result.stderr, (
        "Smoke script must NEVER echo API key values to stderr"
    )


# ---------------------------------------------------------------------------
# Test 9 — smoke script rejects unknown --provider values
# ---------------------------------------------------------------------------


def test_smoke_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing an unsupported --provider value must cause a non-zero exit."""
    env = {**os.environ, "RUN_REAL_LLM_SMOKE": "true"}
    result = subprocess.run(
        [sys.executable, str(_SMOKE_SCRIPT), "--provider", "unsupported_provider_xyz"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_APP_DIR),
        timeout=10,
    )
    assert result.returncode != 0, (
        "Smoke script should reject unsupported --provider with non-zero exit"
    )


# ---------------------------------------------------------------------------
# Test 10 — SUPPORTED_PROVIDERS constant in smoke script contains expected values
# ---------------------------------------------------------------------------


def test_smoke_supported_providers_constant() -> None:
    """Import the smoke script module (without executing main) and verify
    SUPPORTED_PROVIDERS contains the expected provider names."""
    # Add scripts/ to sys.path so we can import smoke_llm_orchestration
    scripts_dir = str(_SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    try:
        # Use importlib to avoid triggering __main__ guard.
        spec = importlib.util.spec_from_file_location(
            "smoke_llm_orchestration", str(_SMOKE_SCRIPT)
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert hasattr(module, "SUPPORTED_PROVIDERS")
        supported = module.SUPPORTED_PROVIDERS
        assert "openai" in supported
        assert "azure_openai" in supported
    finally:
        sys.path[:] = [p for p in sys.path if p != scripts_dir]
        sys.modules.pop("smoke_llm_orchestration", None)
