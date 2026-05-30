"""
app/services/llm_orchestration/__init__.py
-------------------------------------------
Public API for the LLM orchestration service layer.

Exports (Part 1):
    LlmConfigRegistry        — registry class (for testing / advanced use)
    get_registry             — singleton accessor
    resolve_route            — convenience wrapper around route resolver
    LlmOrchestrationError    — base exception
    LlmConfigLoadError       — YAML load failure
    LlmConfigValidationError — validation failure
    LlmRouteNotFoundError    — no route found
    LlmRouteResolutionError  — resolution error

Exports (Part 2):
    PromptResolver           — prompt resolver class (for testing / advanced use)
    get_prompt_resolver      — singleton accessor
    reset_prompt_resolver    — singleton reset (tests only)
    resolve_prompts          — convenience wrapper around prompt resolver
    PromptResolverError      — base prompt exception
    PromptPathError          — invalid or unsafe prompt path
    PromptNotFoundError      — prompt file missing
    PromptValidationError    — prompt file empty or too large

Exports (Part 3):
    LlmOrchestrator              — service-level orchestration coordinator
    MockModelExecutor            — test-only canned model executor
    ModelExecutor                — Protocol for any model backend
    create_mock_orchestrator_for_tests — test factory returning (orchestrator, executor)
    ModelExecutionResult         — normalised executor result schema
    OrchestrationResult          — normalised orchestrator result schema
    LlmOrchestratorError         — base orchestrator error (invalid input etc.)
    LlmExecutionError            — wraps model executor failures

Exports (Part 4):
    ModelConfigResolver          — resolves model/provider metadata from registry
    RegistryBackedModelExecutor  — ModelExecutor backed by registry resolution
    ProviderExecutor             — Protocol for provider adapters
    FakeProviderExecutor         — test-only provider executor
    ResolvedModelConfig          — resolved model/provider metadata schema
    ProviderExecutionRequest     — internal provider execution request schema
    ModelConfigResolutionError   — model/profile resolution failure
    ModelExecutionConfigError    — unsupported execution option
    ProviderExecutionError       — injected provider executor failure
"""

from __future__ import annotations

from schemas.llm_orchestration import (
    ModelExecutionResult,
    OrchestrationResult,
    ProviderExecutionRequest,
    ResolvedModelConfig,
)
from services.llm.orchestration.config_registry import LlmConfigRegistry, get_registry
from services.llm.orchestration.errors import (
    LlmConfigLoadError,
    LlmConfigValidationError,
    LlmExecutionError,
    LlmOrchestrationError,
    LlmOrchestratorError,
    LlmRouteNotFoundError,
    LlmRouteResolutionError,
    ModelConfigResolutionError,
    ModelExecutionConfigError,
    PromptNotFoundError,
    PromptPathError,
    PromptResolverError,
    PromptValidationError,
    ProviderExecutionError,
)
from services.llm.orchestration.model_config_resolver import ModelConfigResolver
from services.llm.orchestration.model_execution import (
    FakeProviderExecutor,
    ProviderExecutor,
    RegistryBackedModelExecutor,
)
from services.llm.orchestration.orchestrator import (
    LlmOrchestrator,
    MockModelExecutor,
    ModelExecutor,
    create_mock_orchestrator_for_tests,
)
from services.llm.orchestration.prompt_resolver import (
    PromptResolver,
    get_prompt_resolver,
    reset_prompt_resolver,
    resolve_prompts,
)
from services.llm.orchestration.route_resolver import resolve_route

__all__ = [
    # Part 1 — config registry
    "LlmConfigRegistry",
    "get_registry",
    # Part 1 — route resolver
    "resolve_route",
    # Part 1 — errors
    "LlmOrchestrationError",
    "LlmConfigLoadError",
    "LlmConfigValidationError",
    "LlmRouteNotFoundError",
    "LlmRouteResolutionError",
    # Part 2 — prompt resolver
    "PromptResolver",
    "get_prompt_resolver",
    "reset_prompt_resolver",
    "resolve_prompts",
    # Part 2 — prompt errors
    "PromptResolverError",
    "PromptPathError",
    "PromptNotFoundError",
    "PromptValidationError",
    # Part 3 — orchestrator
    "LlmOrchestrator",
    "MockModelExecutor",
    "ModelExecutor",
    "create_mock_orchestrator_for_tests",
    # Part 3 — orchestration schemas
    "ModelExecutionResult",
    "OrchestrationResult",
    # Part 3 — orchestrator errors
    "LlmOrchestratorError",
    "LlmExecutionError",
    # Part 4 — model resolution and execution boundary
    "ModelConfigResolver",
    "ProviderExecutor",
    "FakeProviderExecutor",
    "RegistryBackedModelExecutor",
    # Part 4 — schemas
    "ResolvedModelConfig",
    "ProviderExecutionRequest",
    # Part 4 — errors
    "ModelConfigResolutionError",
    "ModelExecutionConfigError",
    "ProviderExecutionError",
]
