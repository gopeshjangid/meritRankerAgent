"""
Parse and validate LLM_ROLE_CONFIG_JSON for the legacy model_router path.

Precedence (orchestrated doubt solver):
  YAML llm_routes.yaml + model_registry.yaml are primary.
  LLM_ROLE_CONFIG_JSON is ignored when ENABLE_ORCHESTRATED_DOUBT_SOLVER=true.

Precedence (legacy path, ENABLE_ORCHESTRATED_DOUBT_SOLVER=false):
  LLM_ROLE_CONFIG_JSON supplies role → model alias OR legacy inline provider config.
  Alias values are resolved against model_registry.yaml (never raw stale deployments).

When a role value is a string alias, model_config_source=llm_role_config_json.
When orchestrated YAML routes are used, model_config_source=yaml.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from schemas.llm import LlmRoleConfig
from services.llm.orchestration.config_registry import get_registry
from services.llm.orchestration.errors import LlmConfigValidationError
from services.llm.providers.errors import LlmConfigurationError

logger = logging.getLogger(__name__)

_LEGACY_PROVIDER_MAP: frozenset[str] = frozenset({"mock", "azure_openai", "openai"})

# Canonical alias map keys (optional override) → registry model alias
_CANONICAL_ROLE_ALIASES: dict[str, str] = {
    "classifier.default": "doubt_solver_classifier",
    "classifier.strong": "doubt_solver_classifier_strong",
    "math.basic": "math_basic_generator",
    "math.intermediate": "math_intermediate_generator",
    "math.advanced": "math_advanced_generator",
    "reasoning.basic": "reasoning_basic_generator",
    "reasoning.intermediate": "reasoning_intermediate_generator",
    "reasoning.advanced": "reasoning_advanced_generator",
    "general.default": "general_fast_generator",
    "current_affairs.default": "general_fast_generator",
    "practice.default": "general_fast_generator",
    "image.extractor": "gemini_image_extractor",
    "experimental.gemini.text": "gemini_flash_text",
    "experimental.deepseek.reasoning": "deepseek_reasoning_generator",
    # Legacy role names used by model_router / answer_generator_service
    "doubt_solver_classifier": "doubt_solver_classifier",
    "doubt_solver_generator": "general_fast_generator",
}


def _is_alias_entry(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_role_config_map(raw_json: str) -> dict[str, Any]:
    """Parse LLM_ROLE_CONFIG_JSON string into a role map."""
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise LlmConfigurationError(
            f"LLM_ROLE_CONFIG_JSON is not valid JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise LlmConfigurationError(
            "LLM_ROLE_CONFIG_JSON must be a JSON object mapping role names to "
            "model aliases (strings) or legacy provider config objects."
        )
    return parsed


def validate_role_config_aliases(role_map: dict[str, Any]) -> None:
    """Fail fast when any alias-based role references an unknown registry alias."""
    registry = get_registry()
    errors: list[str] = []
    for role, value in role_map.items():
        if not _is_alias_entry(value):
            continue
        alias = value.strip()
        if registry.get_model(alias) is None:
            errors.append(f"role={role!r} → unknown model alias {alias!r}")
    if errors:
        raise LlmConfigValidationError(
            "LLM_ROLE_CONFIG_JSON references unknown model aliases: "
            + "; ".join(errors)
        )


def resolve_role_model_alias(role: str, role_map: dict[str, Any]) -> str | None:
    """Return registry model alias for *role*, or None if not configured."""
    if role in role_map:
        value = role_map[role]
        if _is_alias_entry(value):
            return value.strip()
        return None
    canonical = _CANONICAL_ROLE_ALIASES.get(role)
    if canonical and role_map.get(canonical):
        return None
    return None


def model_alias_to_role_config(alias: str) -> LlmRoleConfig:
    """Build legacy LlmRoleConfig from a registry model alias."""
    registry = get_registry()
    model_cfg = registry.get_model(alias)
    if model_cfg is None:
        raise LlmConfigurationError(
            f"LLM_ROLE_CONFIG_JSON alias {alias!r} not found in model registry."
        )

    provider = model_cfg.provider
    if provider not in _LEGACY_PROVIDER_MAP:
        raise LlmConfigurationError(
            f"Legacy model_router does not support provider {provider!r} "
            f"for alias {alias!r}. Use ENABLE_ORCHESTRATED_DOUBT_SOLVER=true "
            "for Gemini/DeepSeek routes."
        )

    deployment = model_cfg.deployment
    model_id = model_cfg.model_id
    if provider == "azure_openai" and not deployment:
        raise LlmConfigurationError(
            f"Azure model alias {alias!r} has no deployment configured. "
            "Set the matching AZURE_OPENAI_DEPLOYMENT_* env var."
        )

    return LlmRoleConfig(
        provider=provider,  # type: ignore[arg-type]
        model_label=alias,
        deployment=deployment,
        model=model_id,
        temperature=0.2,
        max_tokens=1200,
        supports_streaming=model_cfg.supports_streaming,
    )


def resolve_llm_role_config(role: str, role_map: dict[str, Any]) -> tuple[LlmRoleConfig, str]:
    """Resolve role config and return (config, model_config_source)."""
    if role not in role_map:
        raise LlmConfigurationError(
            f"ENABLE_REAL_LLM=true but no role config found for role={role!r}. "
            "Add an entry to LLM_ROLE_CONFIG_JSON for this role."
        )

    value = role_map[role]
    if _is_alias_entry(value):
        alias = value.strip()
        logger.info(
            "llm_role_config  model_config_source=llm_role_config_json  role=%s  alias=%s",
            role,
            alias,
        )
        return model_alias_to_role_config(alias), "llm_role_config_json"

    if isinstance(value, dict):
        logger.info(
            "llm_role_config  model_config_source=llm_role_config_json_legacy  role=%s",
            role,
        )
        return LlmRoleConfig.model_validate(value), "llm_role_config_json_legacy"

    raise LlmConfigurationError(
        f"LLM_ROLE_CONFIG_JSON entry for role={role!r} must be a model alias string "
        "or a legacy provider config object."
    )
