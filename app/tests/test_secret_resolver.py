"""
app/tests/test_secret_resolver.py
-----------------------------------
Tests for EnvSecretResolver (Part 5).

Coverage:
1.  EnvSecretResolver returns env value for valid env var.
2.  Missing env var raises SecretNotFoundError.
3.  Blank env var raises SecretNotFoundError.
4.  Invalid env var name raises SecretResolverConfigError.
5.  Lowercase env var name rejected.
6.  Hyphenated env var name rejected.
7.  Secret-like string passed as env var name rejected (sk-, AIza, AKIA, -----BEGIN).
8.  Resolver does not call load_dotenv.
9.  Resolver does not import boto3 (AST verification).
10. Resolver does not make network calls.
11. Error message does not include secret value.
12. No secret value appears in logs.
13. EnvSecretResolver satisfies the SecretResolver Protocol.

All tests use monkeypatch for env vars — no .env.local dependency.
"""

from __future__ import annotations

import ast
import logging
import pathlib
from unittest.mock import patch

import pytest

from services.secrets.env_secret_resolver import EnvSecretResolver
from services.secrets.errors import SecretNotFoundError, SecretResolverConfigError
from services.secrets.secret_resolver import SecretResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRETS_DIR = pathlib.Path(__file__).parent.parent / "services" / "secrets"
_SECRET_MODULE_NAMES = [
    "env_secret_resolver",
    "secret_resolver",
    "errors",
    "provider_credentials",
]


def _get_all_imports(module_name: str) -> list[tuple[str, str]]:
    """Return (import_type, full_module_name) tuples from a secrets module."""
    path = _SECRETS_DIR / f"{module_name}.py"
    tree = ast.parse(path.read_text())
    results: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(("import", alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                results.append(("from", f"{module}.{alias.name}"))
    return results


# ---------------------------------------------------------------------------
# 1–3: Happy path and missing/blank
# ---------------------------------------------------------------------------


class TestEnvSecretResolverHappyPath:
    """Valid env var reads return the expected value."""

    def test_returns_value_for_valid_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_API_KEY", "test-secret-value")
        resolver = EnvSecretResolver()
        assert resolver.get_secret("MY_API_KEY") == "test-secret-value"

    def test_returns_value_with_alphanumeric_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API123KEY", "val")
        resolver = EnvSecretResolver()
        assert resolver.get_secret("API123KEY") == "val"

    def test_returns_value_with_underscores(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
        resolver = EnvSecretResolver()
        assert resolver.get_secret("GEMINI_API_KEY") == "gemini-test-key"

    def test_returns_value_with_special_chars_in_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TOKEN", "abc123!@#$%^&*()")
        resolver = EnvSecretResolver()
        assert resolver.get_secret("TOKEN") == "abc123!@#$%^&*()"


class TestEnvSecretResolverMissingAndBlank:
    """Missing or blank env vars raise SecretNotFoundError."""

    def test_missing_env_var_raises_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
        resolver = EnvSecretResolver()
        with pytest.raises(SecretNotFoundError):
            resolver.get_secret("MISSING_KEY_XYZ")

    def test_blank_whitespace_env_var_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BLANK_KEY", "   ")
        resolver = EnvSecretResolver()
        with pytest.raises(SecretNotFoundError):
            resolver.get_secret("BLANK_KEY")

    def test_empty_string_env_var_raises_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EMPTY_KEY", "")
        resolver = EnvSecretResolver()
        with pytest.raises(SecretNotFoundError):
            resolver.get_secret("EMPTY_KEY")


# ---------------------------------------------------------------------------
# 4–7: Name validation
# ---------------------------------------------------------------------------


class TestEnvSecretResolverNameValidation:
    """Invalid env var names raise SecretResolverConfigError."""

    def test_empty_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("")

    def test_lowercase_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("my_api_key")

    def test_mixed_case_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("My_Api_Key")

    def test_hyphenated_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("MY-API-KEY")

    def test_dotted_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("MY.API.KEY")

    def test_starts_with_digit_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("1_MY_KEY")

    def test_space_in_name_rejected(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("MY KEY")

    def test_secret_like_sk_prefix_rejected(self) -> None:
        """sk- prefix looks like an OpenAI API key."""
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("sk-1234567890abcdef")

    def test_secret_like_aiza_prefix_rejected(self) -> None:
        """AIza prefix looks like a Google API key."""
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("AIzaSyAbcDefGhiJkl")

    def test_secret_like_akia_prefix_rejected(self) -> None:
        """AKIA prefix looks like an AWS access key ID."""
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("AKIAIOSFODNN7EXAMPLE")

    def test_secret_like_pem_header_rejected(self) -> None:
        """-----BEGIN looks like a PEM certificate."""
        resolver = EnvSecretResolver()
        with pytest.raises(SecretResolverConfigError):
            resolver.get_secret("-----BEGIN RSA PRIVATE KEY-----")


# ---------------------------------------------------------------------------
# 8–10: No side effects
# ---------------------------------------------------------------------------


class TestEnvSecretResolverNoSideEffects:
    """Resolver must not call load_dotenv, boto3, or make network calls.

    Import safety note: we do NOT call importlib.reload() here because
    reloading a module creates new class objects, breaking isinstance/except
    checks in other tests that imported those classes before the reload.
    """

    def test_resolver_does_not_call_load_dotenv(self) -> None:
        """EnvSecretResolver.get_secret() must not call load_dotenv."""
        with patch("dotenv.load_dotenv") as mock_load:
            resolver = EnvSecretResolver()
            try:
                resolver.get_secret("NONEXISTENT_VAR_PART5_TEST")
            except SecretNotFoundError:
                pass
        mock_load.assert_not_called()

    def test_resolver_does_not_import_boto3(self) -> None:
        """No secrets module may import boto3."""
        for module_name in _SECRET_MODULE_NAMES:
            imports = _get_all_imports(module_name)
            for import_type, full_name in imports:
                assert "boto3" not in full_name, (
                    f"services/secrets/{module_name}.py must not import boto3, "
                    f"but found: {import_type} {full_name!r}"
                )

    def test_resolver_does_not_import_provider_sdks(self) -> None:
        """No secrets module may import provider SDKs."""
        banned = ["openai", "anthropic", "google", "azure"]
        for module_name in _SECRET_MODULE_NAMES:
            imports = _get_all_imports(module_name)
            for _import_type, full_name in imports:
                for sdk in banned:
                    assert sdk not in full_name, (
                        f"services/secrets/{module_name}.py must not import {sdk!r}, "
                        f"but found: {full_name!r}"
                    )

    def test_resolver_does_not_make_network_calls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret() must not open any network connections."""
        import socket

        connection_attempts: list[object] = []
        original_connect = socket.socket.connect

        def spy_connect(self: socket.socket, address: object) -> None:  # type: ignore[override]
            connection_attempts.append(address)
            return original_connect(self, address)

        monkeypatch.setattr(socket.socket, "connect", spy_connect)
        monkeypatch.setenv("MY_SAFE_KEY", "test-value")
        resolver = EnvSecretResolver()
        resolver.get_secret("MY_SAFE_KEY")
        assert connection_attempts == [], (
            f"EnvSecretResolver made unexpected network calls to: {connection_attempts}"
        )


# ---------------------------------------------------------------------------
# 11–12: Secret value safety
# ---------------------------------------------------------------------------


class TestSecretValueSafety:
    """Error messages and logs must never expose secret values."""

    def test_not_found_error_message_includes_var_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SecretNotFoundError message should contain the env var name."""
        monkeypatch.delenv("MISSING_KEY_ABC", raising=False)
        resolver = EnvSecretResolver()
        with pytest.raises(SecretNotFoundError, match="MISSING_KEY_ABC"):
            resolver.get_secret("MISSING_KEY_ABC")

    def test_blank_error_message_does_not_include_secret_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SecretNotFoundError for a blank var must include the var name, not value."""
        monkeypatch.setenv("BLANK_KEY", "   ")
        resolver = EnvSecretResolver()
        with pytest.raises(SecretNotFoundError) as exc_info:
            resolver.get_secret("BLANK_KEY")
        # Error message must include var name for debuggability
        assert "BLANK_KEY" in str(exc_info.value)
        # Error message must not expose the raw value (only whitespace in this case)
        assert "sk-" not in str(exc_info.value)

    def test_no_secret_value_in_logs_on_success(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Successful get_secret() must not log the resolved value."""
        monkeypatch.setenv("LOG_TEST_KEY", "my-secret-must-not-appear-in-log")
        resolver = EnvSecretResolver()
        with caplog.at_level(logging.DEBUG):
            result = resolver.get_secret("LOG_TEST_KEY")
        assert result == "my-secret-must-not-appear-in-log"
        assert "my-secret-must-not-appear-in-log" not in caplog.text

    def test_no_secret_value_in_logs_on_error(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Failed get_secret() must not log the (blank) value either."""
        monkeypatch.setenv("BLANK_LOG_KEY", "  hidden-value  ")
        resolver = EnvSecretResolver()
        with caplog.at_level(logging.DEBUG):
            try:
                resolver.get_secret("BLANK_LOG_KEY")
            except SecretNotFoundError:
                pass
        assert "hidden-value" not in caplog.text


# ---------------------------------------------------------------------------
# 13: Protocol conformance
# ---------------------------------------------------------------------------


class TestSecretResolverProtocol:
    """EnvSecretResolver satisfies the SecretResolver Protocol."""

    def test_env_resolver_is_instance_of_secret_resolver(self) -> None:
        resolver = EnvSecretResolver()
        assert isinstance(resolver, SecretResolver)

    def test_env_resolver_has_get_secret_method(self) -> None:
        resolver = EnvSecretResolver()
        assert callable(getattr(resolver, "get_secret", None))
