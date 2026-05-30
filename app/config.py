"""
app/config.py
-------------
Application settings loaded from environment variables.

Priority order (highest → lowest):
  1. Real environment variables (set by agentcore dev or shell)
  2. app/.env.local  (local secrets, gitignored)
  3. Hardcoded defaults below

Never log secrets. Keep this module import-safe and side-effect-free
except for the load_dotenv call at module load time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env.local sitting next to this file.
# override=False means real env vars always win — safe for production too.
_env_file = Path(__file__).parent / ".env.local"
load_dotenv(_env_file, override=False)


class ConfigurationError(Exception):
    """Raised when the application is misconfigured at startup.

    This is a fail-fast error — it is raised during module-level graph
    construction (before any request is processed) so operators can identify
    and fix the misconfiguration before the process accepts traffic.

    Example: ENABLE_ORCHESTRATED_DOUBT_SOLVER=true with ENABLE_REAL_LLM=false
             when APP_ENV=production (would silently return mock answers).
    """

@dataclass(frozen=True)
class Settings:
    """Immutable settings snapshot.  All values come from os.environ."""

    app_env: str
    log_level: str
    model_provider: str
    # LLM routing
    enable_real_llm: bool
    llm_default_provider: str
    llm_role_config_json: str  # raw JSON string — parsed by get_llm_role_config()
    # Orchestrated doubt solver path (enabled via ENABLE_ORCHESTRATED_DOUBT_SOLVER)
    enable_orchestrated_doubt_solver: bool
    # Safety override: allow mock orchestrated executor outside normal non-production
    # gating.  Set ENABLE_ORCHESTRATED_MOCK_LLM=true ONLY for controlled internal
    # testing.  Must NEVER be set in normal production deployments.
    enable_orchestrated_mock_llm: bool
    # Bedrock Knowledge Base retrieval
    enable_kb_retrieval: bool
    bedrock_kb_id: str
    bedrock_kb_region: str  # empty string means "use AWS_REGION or boto3 default"
    bedrock_kb_max_results: int
    bedrock_kb_min_score: float | None  # None means "no minimum threshold"
    # DynamoDB record fetch
    enable_dynamodb_fetch: bool
    dynamodb_question_table: str
    dynamodb_pattern_table: str
    dynamodb_default_index: str  # empty string means "no default index"
    dynamodb_region: str  # empty string means "use AWS_REGION or boto3 default"
    # Context builder
    doubt_solver_max_context_chars: int  # hard cap on context string passed to answer generator


# Module-level singleton — built once on first call to get_settings().
_settings: Settings | None = None


def _parse_optional_float(value: str) -> float | None:
    """Return a float if *value* is non-empty and parseable, else None."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Reads os.environ at first call.  Subsequent calls return the cached object
    so environment variables are not re-read mid-request.
    """
    global _settings
    if _settings is None:
        _settings = Settings(
            app_env=os.getenv("APP_ENV", "local"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            model_provider=os.getenv("MODEL_PROVIDER", "mock"),
            enable_real_llm=os.getenv("ENABLE_REAL_LLM", "false").lower() == "true",
            llm_default_provider=os.getenv("LLM_DEFAULT_PROVIDER", "mock"),
            llm_role_config_json=os.getenv("LLM_ROLE_CONFIG_JSON", "{}"),
            enable_orchestrated_doubt_solver=(
                os.getenv("ENABLE_ORCHESTRATED_DOUBT_SOLVER", "false").lower() == "true"
            ),
            enable_orchestrated_mock_llm=(
                os.getenv("ENABLE_ORCHESTRATED_MOCK_LLM", "false").lower() == "true"
            ),
            enable_kb_retrieval=os.getenv("ENABLE_KB_RETRIEVAL", "false").lower() == "true",
            bedrock_kb_id=os.getenv("BEDROCK_KB_ID", ""),
            bedrock_kb_region=os.getenv(
                "BEDROCK_KB_REGION", os.getenv("AWS_REGION", "")
            ),
            bedrock_kb_max_results=int(os.getenv("BEDROCK_KB_MAX_RESULTS", "5")),
            bedrock_kb_min_score=_parse_optional_float(
                os.getenv("BEDROCK_KB_MIN_SCORE", "")
            ),
            enable_dynamodb_fetch=os.getenv("ENABLE_DYNAMODB_FETCH", "false").lower() == "true",
            dynamodb_question_table=os.getenv("DYNAMODB_QUESTION_TABLE", ""),
            dynamodb_pattern_table=os.getenv("DYNAMODB_PATTERN_TABLE", ""),
            dynamodb_default_index=os.getenv("DYNAMODB_DEFAULT_INDEX", ""),
            dynamodb_region=os.getenv(
                "DYNAMODB_REGION", os.getenv("AWS_REGION", "")
            ),
            doubt_solver_max_context_chars=int(
                os.getenv("DOUBT_SOLVER_MAX_CONTEXT_CHARS", "6000")
            ),
        )
    return _settings


def get_llm_role_config(role: str, settings: Settings | None = None):  # -> LlmRoleConfig
    """Return the LlmRoleConfig for a named role.

    When ENABLE_REAL_LLM=false (default), any role not found in the config map
    falls back to a local mock config so development works without credentials.

    When ENABLE_REAL_LLM=true, a missing role config is a hard error — the
    caller must supply a complete LLM_ROLE_CONFIG_JSON.

    Args:
        role:     The named role to look up (e.g. 'classifier', 'solver').
        settings: Optional Settings override for testing.  Uses get_settings()
                  when None.

    Returns:
        LlmRoleConfig for the role.

    Raises:
        LlmConfigurationError: If the JSON is malformed, or if ENABLE_REAL_LLM=true
                               and no config exists for the given role.
    """
    # Deferred imports prevent circular-import issues at module load time.
    from schemas.llm import LlmRoleConfig  # noqa: PLC0415
    from services.llm.providers.errors import LlmConfigurationError  # noqa: PLC0415

    s = settings or get_settings()

    try:
        role_map: dict = json.loads(s.llm_role_config_json)
    except json.JSONDecodeError as exc:
        raise LlmConfigurationError(
            f"LLM_ROLE_CONFIG_JSON is not valid JSON: {exc}"
        ) from exc

    if role in role_map:
        return LlmRoleConfig.model_validate(role_map[role])

    # Role not found in config map.
    if s.enable_real_llm:
        raise LlmConfigurationError(
            f"ENABLE_REAL_LLM=true but no role config found for role={role!r}. "
            "Add an entry to LLM_ROLE_CONFIG_JSON for this role."
        )

    # Safe default: mock provider, no credentials required.
    return LlmRoleConfig(
        provider="mock",
        model_label="local-mock",
        supports_streaming=True,
    )
