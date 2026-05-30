"""
app/services/secrets/env_secret_resolver.py
---------------------------------------------
EnvSecretResolver — reads secrets from the process environment.

Design rules:
- Reads ``os.environ`` at resolve time only (never at import time).
- Does NOT call ``load_dotenv`` — callers must ensure env vars are set.
- Does NOT cache values.
- Validates the env var name before reading the value.
- Raises ``SecretNotFoundError`` if the variable is missing or blank.
- Raises ``SecretResolverConfigError`` for invalid env var names.
- Never logs the secret value.

Usage (local development):
    resolver = EnvSecretResolver()
    api_key = resolver.get_secret("OPENAI_API_KEY")

Production:
    Use SecretsManagerSecretResolver or AgentCoreIdentitySecretResolver
    (both deferred — see [DEFER] tags in errors.py).
"""

from __future__ import annotations

import os
import re

from services.secrets.errors import SecretNotFoundError, SecretResolverConfigError

# Env var names must be SCREAMING_SNAKE_CASE: start with uppercase letter,
# followed by uppercase letters, digits, or underscores.
_ENV_VAR_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

# Reject names that look like raw secret values accidentally passed as a name.
# This catches common mistakes: OpenAI keys, Google API keys, AWS access key IDs,
# PEM certificate headers.
_SECRET_LIKE_PATTERN = re.compile(r"(^sk-|^AIza|^AKIA|-----BEGIN)", re.IGNORECASE)


class EnvSecretResolver:
    """Reads secrets from ``os.environ``.

    This resolver is for local development only.  It does not call
    ``load_dotenv`` — callers must ensure the env vars are set before
    invoking this resolver (e.g. via a ``.env.local`` file loaded by
    the application entrypoint, or set explicitly in tests via monkeypatch).

    Production deployments should use ``SecretsManagerSecretResolver`` or
    ``AgentCoreIdentitySecretResolver`` (both deferred — see [DEFER]).
    """

    def get_secret(self, name: str) -> str:
        """Read a secret from ``os.environ``.

        Validates the env var name, then reads and returns the value.
        Never logs the value.

        Args:
            name: SCREAMING_SNAKE_CASE environment variable name.

        Returns:
            The env var value as a non-empty string.

        Raises:
            SecretResolverConfigError: If ``name`` is empty, not
                SCREAMING_SNAKE_CASE, or looks like a raw secret value.
            SecretNotFoundError: If the env var is not set, or the value
                is empty or blank.
        """
        self._validate_name(name)

        value = os.environ.get(name)
        if value is None:
            raise SecretNotFoundError(
                f"Environment variable '{name}' is not set."
            )
        if not value.strip():
            raise SecretNotFoundError(
                f"Environment variable '{name}' is set but has a blank value."
            )
        return value

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate that ``name`` is a safe env var name identifier.

        Checks are applied in order: empty, secret-like, not SCREAMING_SNAKE_CASE.
        """
        if not name:
            raise SecretResolverConfigError(
                "Secret name must not be empty."
            )
        if _SECRET_LIKE_PATTERN.search(name):
            raise SecretResolverConfigError(
                "Secret name looks like a raw secret value "
                "(matched pattern: sk-, AIza, AKIA, or '-----BEGIN'). "
                "Pass the environment variable NAME, not the secret value itself."
            )
        if not _ENV_VAR_PATTERN.match(name):
            raise SecretResolverConfigError(
                f"Secret name {name!r} is not a valid environment variable name. "
                "Must match ^[A-Z][A-Z0-9_]*$ (SCREAMING_SNAKE_CASE)."
            )
