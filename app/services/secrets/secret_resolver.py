"""
app/services/secrets/secret_resolver.py
-----------------------------------------
SecretResolver protocol — the interface for all secret resolution backends.

Design rules:
- Resolvers return secret values as plain strings.
- Resolvers must never log the secret value.
- Resolvers must raise SecretResolverError subclasses on failure.
- The ``name`` parameter identifies the secret (env var name, Secrets Manager
  secret name, etc.) — it is never the secret value itself.

Deferred implementations (Part 5 only defines the protocol):
- SecretsManagerSecretResolver — [DEFER] AWS Secrets Manager backend.
- AgentCoreIdentitySecretResolver — [DEFER] AgentCore Identity backend.

No boto3, no AgentCore SDK, no network calls in this module.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.secrets.errors import SecretResolverError  # noqa: F401 — re-exported for callers


@runtime_checkable
class SecretResolver(Protocol):
    """Interface for secret resolution backends.

    Implementors:
    - ``EnvSecretResolver``: reads from ``os.environ`` (Part 5 — local dev).
    - ``SecretsManagerSecretResolver``: AWS Secrets Manager [DEFER].
    - ``AgentCoreIdentitySecretResolver``: AgentCore Identity [DEFER].

    Rules:
    - ``name`` must be a non-empty identifier string.
    - The returned value is the secret string.
    - Must never log the returned value.
    - Must raise ``SecretResolverError`` subclasses on failure.
    """

    def get_secret(self, name: str) -> str:
        """Resolve a secret by name and return its value.

        Args:
            name: The identifier for the secret.  For ``EnvSecretResolver``
                  this is an environment variable name (SCREAMING_SNAKE_CASE).
                  For future backends it may be a secret ARN or credential
                  resource name.

        Returns:
            The resolved secret value as a non-empty string.

        Raises:
            SecretResolverConfigError: If ``name`` is invalid or unsafe.
            SecretNotFoundError: If the secret cannot be found or has no value.
            SecretResolverUnsupportedError: If the resolver does not support
                this type of resolution.
            SecretResolverError: For other resolver failures.
        """
        ...
