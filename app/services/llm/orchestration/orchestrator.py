"""
app/services/llm_orchestration/orchestrator.py
------------------------------------------------
LlmOrchestrator — service-level coordinator for the orchestration layer (Part 3).

Responsibilities:
- Accept a RouteRequest + query + optional classification + optional context.
- Resolve a RouteDecision via an injected route resolver function.
- Build composed LlmMessages via an injected PromptResolver.
- Call the injected ModelExecutor boundary.
- Return a safe, normalised OrchestrationResult.

Design invariants:
- No LLM provider SDK calls.
- No AWS calls.
- No YAML parsing.
- No prompt file reading directly; delegates to PromptResolver.
- No secrets fetched, no secrets logged.
- Query and context are NEVER logged.
- model_executor is always required — no implicit mock in production path.

Non-goals (deferred):
- Real model_router / provider adapter wiring (Part 5+).
- SecretResolver.
- AgentCore config bundle prompt source.
- Langfuse prompt management.
- Provider-level fallback.
- Graph node integration.
- Memory, cache, verifier, visual formatter.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from typing import Any, Protocol, runtime_checkable

from schemas.llm import LlmMessage
from schemas.llm_orchestration import ModelExecutionResult, OrchestrationResult
from schemas.llm_routing import RouteDecision, RouteRequest
from services.llm.orchestration.errors import (
    LlmExecutionError,
    LlmOrchestrationError,
    LlmOrchestratorError,
)
from services.llm.orchestration.prompt_resolver import PromptResolver, get_prompt_resolver
from services.llm.orchestration.route_resolver import resolve_route

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_QUERY_CHARS: int = 4_000

# ---------------------------------------------------------------------------
# ModelExecutor Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ModelExecutor(Protocol):
    """Minimal boundary for any model backend.

    Implementations must be stateless between calls except for optional
    recording of the last call (for testing purposes).
    """

    def execute(
        self,
        *,
        route_decision: RouteDecision,
        messages: list[LlmMessage],
    ) -> ModelExecutionResult:
        """Execute a model call and return the normalised result.

        Args:
            route_decision: The resolved route (model alias, temperature, etc.).
            messages:       The composed system + user messages from PromptResolver.

        Returns:
            ModelExecutionResult with content and safe metadata.

        Raises:
            Any exception — LlmOrchestrator wraps it as LlmExecutionError.
        """
        ...

    def execute_stream(
        self,
        *,
        route_decision: RouteDecision,
        messages: list[LlmMessage],
    ) -> Iterator[str]:
        """Execute a model call and yield answer text chunks."""
        ...


# ---------------------------------------------------------------------------
# MockModelExecutor
# ---------------------------------------------------------------------------


class MockModelExecutor:
    """Test-only ModelExecutor that returns a configurable canned response.

    Usage:
        orchestrator, executor = create_mock_orchestrator_for_tests(content="2+2=4")
        result = orchestrator.generate(route_request=..., query="What is 2+2?")
        assert result.content == "2+2=4"
        assert executor.call_count == 1

    Attributes:
        last_route_decision: The RouteDecision from the most recent execute() call.
        last_messages:       The messages list from the most recent execute() call.
        call_count:          Total number of execute() invocations since construction.
    """

    def __init__(
        self,
        content: str = "Mock response.",
        raise_on_execute: Exception | None = None,
        provider: str | None = "mock",
        fallback_used: bool = False,
    ) -> None:
        self._content = content
        self._raise_on_execute = raise_on_execute
        self._provider = provider
        self._fallback_used = fallback_used
        self.last_route_decision: RouteDecision | None = None
        self.last_messages: list[LlmMessage] | None = None
        self.call_count: int = 0

    def execute(
        self,
        *,
        route_decision: RouteDecision,
        messages: list[LlmMessage],
    ) -> ModelExecutionResult:
        """Record the call, optionally raise, or return canned content."""
        self.last_route_decision = route_decision
        self.last_messages = messages
        self.call_count += 1

        if self._raise_on_execute is not None:
            raise self._raise_on_execute

        return ModelExecutionResult(
            content=self._content,
            model=route_decision.model,
            provider=self._provider,
            fallback_used=self._fallback_used,
        )

    def execute_stream(
        self,
        *,
        route_decision: RouteDecision,
        messages: list[LlmMessage],
    ) -> Iterator[str]:
        """Record the call, optionally raise, or yield canned content in chunks."""
        self.last_route_decision = route_decision
        self.last_messages = messages
        self.call_count += 1

        if self._raise_on_execute is not None:
            raise self._raise_on_execute

        chunk_size = 8
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i : i + chunk_size]


# ---------------------------------------------------------------------------
# LlmOrchestrator
# ---------------------------------------------------------------------------


class LlmOrchestrator:
    """Coordinates route resolution, prompt composition, and model execution.

    Constructor:
        model_executor:    Required.  Any object conforming to ModelExecutor
                           protocol.  No default — callers must inject one.
        route_resolver_fn: Optional callable with signature
                           ``(RouteRequest) -> RouteDecision``.  Defaults to
                           the module-level ``resolve_route`` from Part 1.
        prompt_resolver:   Optional PromptResolver instance.  Defaults to the
                           module-level singleton from Part 2 (reads real
                           app/prompts/).  Inject a PromptResolver(tmp_path)
                           in tests.
    """

    def __init__(
        self,
        *,
        model_executor: ModelExecutor,
        route_resolver_fn: Callable[[RouteRequest], RouteDecision] | None = None,
        prompt_resolver: PromptResolver | None = None,
    ) -> None:
        self._model_executor = model_executor
        self._route_resolver_fn: Callable[[RouteRequest], RouteDecision] = (
            route_resolver_fn if route_resolver_fn is not None else resolve_route
        )
        self._prompt_resolver: PromptResolver = (
            prompt_resolver if prompt_resolver is not None else get_prompt_resolver()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        route_request: RouteRequest,
        query: str,
        classification: Any | None = None,
        context: str | None = None,
    ) -> OrchestrationResult:
        """Run the full orchestration pipeline and return a safe result.

        Steps:
            1. Validate query (non-empty, within MAX_QUERY_CHARS).
            2. Resolve route via route_resolver_fn.
            3. Build messages via prompt_resolver.resolve().
            4. Call model_executor.execute().
            5. Wrap executor exceptions as LlmExecutionError.
            6. Build and return OrchestrationResult.

        Safe logging:
            Logs request_id, route_id, subject, task_role, difficulty, model,
            fallback_used, and latency_ms only.  Never logs query, context,
            classification data, or prompt content.

        Raises:
            LlmOrchestratorError:    Invalid query (empty or over limit).
            LlmExecutionError:       model_executor.execute() raised an exception.
            LlmRouteNotFoundError:   route_resolver_fn could not find a route.
            LlmRouteResolutionError: Unexpected route resolution error.
            PromptResolverError:     Prompt file missing, unsafe path, or invalid
                                     content.
        """
        # --- 1. Input validation -------------------------------------------
        if not query or not query.strip():
            raise LlmOrchestratorError("Query must not be empty.")
        if len(query) > MAX_QUERY_CHARS:
            raise LlmOrchestratorError(
                f"Query exceeds maximum allowed length of {MAX_QUERY_CHARS} characters."
            )

        start_ms = int(time.monotonic() * 1000)

        # --- 2. Route resolution -------------------------------------------
        route_decision: RouteDecision = self._route_resolver_fn(route_request)

        # --- 3. Prompt composition -----------------------------------------
        messages: list[LlmMessage] = self._prompt_resolver.resolve(
            route_decision,
            query,
            classification,
            context,
        )

        # --- 4. Model execution -------------------------------------------
        try:
            execution_result: ModelExecutionResult = self._model_executor.execute(
                route_decision=route_decision,
                messages=messages,
            )
        except LlmOrchestrationError:
            # Controlled orchestration-layer errors bubble unchanged.
            raise
        except Exception as exc:
            raise LlmExecutionError(
                f"Model executor raised an unexpected error for route "
                f"'{route_decision.route_id}': {type(exc).__name__}"
            ) from exc

        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        # --- 5. Derive answer_source ---------------------------------------
        answer_source = _derive_answer_source(execution_result)

        # --- 6. Safe logging -----------------------------------------------
        logger.info(
            "llm_orchestrator.generate  request_id=%s  route_id=%s  subject=%s  "
            "task_role=%s  difficulty=%s  model=%s  fallback_used=%s  latency_ms=%d",
            route_request.request_id,
            route_decision.route_id,
            route_decision.subject,
            route_decision.task_role,
            route_decision.difficulty,
            route_decision.model,
            execution_result.fallback_used,
            elapsed_ms,
        )

        # --- 7. Build OrchestrationResult ----------------------------------
        return OrchestrationResult(
            content=execution_result.content,
            route_decision=route_decision,
            model=execution_result.model,
            provider=execution_result.provider,
            fallback_used=execution_result.fallback_used,
            finish_reason=execution_result.finish_reason,
            input_tokens=execution_result.input_tokens,
            output_tokens=execution_result.output_tokens,
            latency_ms=execution_result.latency_ms,
            answer_source=answer_source,
            metadata={},
        )

    def generate_stream(
        self,
        *,
        route_request: RouteRequest,
        query: str,
        classification: Any | None = None,
        context: str | None = None,
    ) -> Iterator[str]:
        """Run orchestration and yield answer text chunks from the model executor."""
        if not query or not query.strip():
            raise LlmOrchestratorError("Query must not be empty.")
        if len(query) > MAX_QUERY_CHARS:
            raise LlmOrchestratorError(
                f"Query exceeds maximum allowed length of {MAX_QUERY_CHARS} characters."
            )

        start_ms = int(time.monotonic() * 1000)
        route_decision: RouteDecision = self._route_resolver_fn(route_request)
        messages: list[LlmMessage] = self._prompt_resolver.resolve(
            route_decision,
            query,
            classification,
            context,
        )

        chunk_count = 0
        try:
            for chunk in self._model_executor.execute_stream(
                route_decision=route_decision,
                messages=messages,
            ):
                chunk_count += 1
                yield chunk
        except LlmOrchestrationError:
            raise
        except Exception as exc:
            raise LlmExecutionError(
                f"Model executor stream raised an unexpected error for route "
                f"'{route_decision.route_id}': {type(exc).__name__}"
            ) from exc

        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        logger.info(
            "llm_orchestrator.generate_stream  request_id=%s  route_id=%s  subject=%s  "
            "task_role=%s  difficulty=%s  model=%s  chunk_count=%d  latency_ms=%d",
            route_request.request_id,
            route_decision.route_id,
            route_decision.subject,
            route_decision.task_role,
            route_decision.difficulty,
            route_decision.model,
            chunk_count,
            elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_answer_source(
    execution_result: ModelExecutionResult,
) -> str:
    """Derive answer_source from the execution result's provenance."""
    if execution_result.fallback_used:
        return "fallback"
    if execution_result.provider is None or execution_result.provider == "mock":
        return "mock"
    return "llm"


# ---------------------------------------------------------------------------
# Test factory
# ---------------------------------------------------------------------------


def create_mock_orchestrator_for_tests(
    content: str = "Mock response.",
    prompt_resolver: PromptResolver | None = None,
    route_resolver_fn: Callable[[RouteRequest], RouteDecision] | None = None,
    raise_on_execute: Exception | None = None,
) -> tuple[LlmOrchestrator, MockModelExecutor]:
    """Create a fully-injected LlmOrchestrator backed by a MockModelExecutor.

    Returns both the orchestrator and the executor so tests can inspect
    ``executor.last_messages``, ``executor.last_route_decision``, and
    ``executor.call_count`` after calling ``orchestrator.generate()``.

    Args:
        content:           Text the mock executor returns as generated content.
        prompt_resolver:   Optional PromptResolver.  Pass ``PromptResolver(tmp_path)``
                           in tests that need prompt file isolation.  If None,
                           the module-level singleton (reading real app/prompts/)
                           is used.
        route_resolver_fn: Optional callable that overrides route resolution.
                           Useful for returning a fixed RouteDecision without
                           needing a real registry YAML.
        raise_on_execute:  If provided, the mock executor raises this exception
                           on execute() — for testing LlmExecutionError wrapping.

    Returns:
        ``(LlmOrchestrator, MockModelExecutor)``
    """
    executor = MockModelExecutor(content=content, raise_on_execute=raise_on_execute)
    orchestrator = LlmOrchestrator(
        model_executor=executor,
        route_resolver_fn=route_resolver_fn,
        prompt_resolver=prompt_resolver,
    )
    return orchestrator, executor
