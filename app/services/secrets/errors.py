"""
app/services/secrets/errors.py
--------------------------------
Exception hierarchy for the secret resolver layer (Part 5).

Rules:
- Error messages must never include actual secret values.
- Missing env var errors may include the env var name (not the value).
- Unsupported credential_ref errors may include the reference name only if
  it does not look like a raw secret value; otherwise use a generic message.
"""

from __future__ import annotations


class SecretResolverError(Exception):
    """Base class for all secret resolver errors."""


class SecretResolverConfigError(SecretResolverError):
    """Raised when the resolver is called with an invalid configuration.

    Examples:
    - env var name does not match ^[A-Z][A-Z0-9_]*$
    - env var name looks like a raw secret value passed by mistake
    """


class SecretNotFoundError(SecretResolverError):
    """Raised when a secret cannot be resolved.

    Examples:
    - env var is not set in the process environment
    - env var is set but the value is empty or blank
    """


class SecretResolverUnsupportedError(SecretResolverError):
    """Raised when a resolver is asked to perform an unsupported operation.

    Examples:
    - credential_ref resolution is not yet implemented in Part 5
    - SecretsManagerSecretResolver is deferred [DEFER]
    - AgentCoreIdentitySecretResolver is deferred [DEFER]
    """
