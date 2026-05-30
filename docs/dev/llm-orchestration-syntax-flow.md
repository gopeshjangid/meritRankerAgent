# LLM Orchestration Syntax Flow (Beginner-Friendly)

This guide explains what is happening in the orchestration layer, how data flows through it, and why the code uses these patterns.

Audience:
- Developers learning this codebase.
- Anyone new to Protocols, Pydantic schemas, dependency injection, and service boundaries.

---

## 1) Big Picture: What Problem This Solves

The orchestration layer decides three things safely and deterministically:

1. Which route to use for the request.
2. Which prompt messages to build.
3. Which model/provider metadata should be used for execution.

Then it delegates execution to an injected boundary, so business logic stays clean and testable.

High-level pipeline:

```mermaid
flowchart LR
  A[RouteRequest + query] --> B[RouteResolver]
  B --> C[RouteDecision]
  C --> D[PromptResolver]
  D --> E[list[LlmMessage]]
  C --> F[ModelConfigResolver]
  F --> G[ResolvedModelConfig]
  E --> H[RegistryBackedModelExecutor]
  G --> H
  H --> I[ProviderExecutor (Fake in tests)]
  I --> J[ModelExecutionResult]
  J --> K[LlmOrchestrator]
  K --> L[OrchestrationResult (safe output)]
```

Why this structure:
- Deterministic routing and prompt composition.
- Provider details hidden behind a boundary.
- No secrets or prompt/query/context leakage in public output.
- Easy unit testing without network or cloud dependencies.

---

## 2) Core Files and Their Responsibilities

### Routing and config compile (Part 1)
- [app/services/llm_orchestration/config_registry.py](app/services/llm_orchestration/config_registry.py)
- [app/services/llm_orchestration/route_resolver.py](app/services/llm_orchestration/route_resolver.py)
- [app/schemas/llm_routing.py](app/schemas/llm_routing.py)

What happens:
- YAML is loaded once, validated with Pydantic, then compiled into maps.
- At request time, route lookup is dictionary lookup only.
- Result is a `RouteDecision` (model alias + prompt path + options + fallback metadata).

Why:
- Performance: no YAML parse per request.
- Safety: validation catches bad config early.
- Determinism: route resolver is pure logic.

### Prompt building (Part 2)
- [app/services/llm_orchestration/prompt_resolver.py](app/services/llm_orchestration/prompt_resolver.py)

What happens:
- Validates prompt paths (no `..`, no URL, no absolute path, `.md` only).
- Loads main prompt + overlays.
- Builds exactly 2 messages: `system` and `user`.
- Puts query/context only in user message.

Why:
- Prompt injection surface reduced.
- Consistent message structure for downstream executor.

### Orchestration coordinator (Part 3)
- [app/services/llm_orchestration/orchestrator.py](app/services/llm_orchestration/orchestrator.py)
- [app/schemas/llm_orchestration.py](app/schemas/llm_orchestration.py)

What happens:
- Validates query (non-empty, max length).
- Calls route resolver and prompt resolver.
- Calls injected `ModelExecutor`.
- Returns safe `OrchestrationResult`.

Why:
- One place coordinates steps.
- Dependencies injected, so tests can swap fake executors.

### Model execution boundary (Part 4)
- [app/services/llm_orchestration/model_config_resolver.py](app/services/llm_orchestration/model_config_resolver.py)
- [app/services/llm_orchestration/model_execution.py](app/services/llm_orchestration/model_execution.py)

What happens:
- Resolves `RouteDecision.model` alias into `ModelConfig + ProviderProfile` metadata.
- Validates provider options (e.g. `thinking=true` requires `supports_thinking=true`).
- Builds internal `ProviderExecutionRequest`.
- Delegates to injected `ProviderExecutor`.

Why:
- Isolates provider-facing execution path.
- Prepares architecture for real provider adapters later.
- Keeps secrets and network logic out of orchestration core.

---

## 3) Step-by-Step Runtime Flow (Exact Sequence)

### Input
You call `LlmOrchestrator.generate(...)` with:
- `route_request` (subject, role, difficulty, etc.)
- `query`
- optional `classification`
- optional `context`

### Step A: Query guardrails
In [app/services/llm_orchestration/orchestrator.py](app/services/llm_orchestration/orchestrator.py):
- Reject empty/whitespace query.
- Reject query length above `MAX_QUERY_CHARS`.

Reason:
- Early validation avoids wasted work and accidental huge prompts.

### Step B: Route resolution
`resolve_route(...)` returns `RouteDecision` from maps.

Reason:
- Route decision is deterministic and independent of model output.

### Step C: Prompt resolution
`PromptResolver.resolve(...)` returns `list[LlmMessage]` with 2 messages.

Reason:
- Clear system/user split.
- Security control over where user data appears.

### Step D: Model execution boundary
The injected `ModelExecutor` runs.

Current Part 4 path:
- `RegistryBackedModelExecutor.execute(...)`
- `ModelConfigResolver.resolve(route_decision)`
- Build `ProviderExecutionRequest`
- `provider_executor.execute(request)`

In tests, `FakeProviderExecutor` is used.

Reason:
- Clean contract, real provider integration can be plugged later.

### Step E: Safe public output
Return `OrchestrationResult`.

Important:
- No `messages`, no query, no context, no prompt text.
- Metadata validators reject sensitive keys.

Reason:
- Prevent sensitive or prompt internals from leaking across layer boundaries.

---

## 4) Syntax Concepts Used (and Why)

## 4.1 Protocols (structural typing)
Where:
- `ModelExecutor` in [app/services/llm_orchestration/orchestrator.py](app/services/llm_orchestration/orchestrator.py)
- `ProviderExecutor` in [app/services/llm_orchestration/model_execution.py](app/services/llm_orchestration/model_execution.py)

What it means:
- Any class with the required method signature is accepted.
- No hard inheritance required.

Why used:
- Easy test fakes/mocks.
- Future provider adapters can plug in without changing orchestration code.

## 4.2 Dependency Injection
Where:
- `LlmOrchestrator(... model_executor=...)`
- `RegistryBackedModelExecutor(... provider_executor=...)`

What it means:
- Dependencies are passed in, not created internally.

Why used:
- Testability, flexibility, lower coupling.

## 4.3 Pydantic v2 schemas
Where:
- [app/schemas/llm_routing.py](app/schemas/llm_routing.py)
- [app/schemas/llm_orchestration.py](app/schemas/llm_orchestration.py)

What it means:
- Runtime validation for structured data.

Why used:
- Invalid config/request/metadata fails early with clear errors.
- Strong contracts between layers.

## 4.4 Field validators and model validators
Examples in [app/schemas/llm_orchestration.py](app/schemas/llm_orchestration.py):
- Reject unsafe metadata keys.
- Validate non-negative token counts.
- Validate answer source consistency (`fallback` implies `fallback_used=True`).

Why used:
- Security and correctness enforced at schema boundary.

## 4.5 Safe logging pattern
Where:
- [app/services/llm_orchestration/orchestrator.py](app/services/llm_orchestration/orchestrator.py)
- [app/services/llm_orchestration/model_execution.py](app/services/llm_orchestration/model_execution.py)

What is logged:
- Route ID, model alias, provider, capability flags, latency.

What is not logged:
- Prompt text, query, context, full messages, secrets.

Why used:
- Observability without data leakage.

---

## 5) Why `RouteDecision.model` Is an Alias (Not Raw Provider Model ID)

`RouteDecision.model` is intentionally a model alias (for example, `gemini_flash_light`).

Then Part 4 resolves alias to metadata through registry maps:
- alias -> `ModelConfig`
- `provider_profile` name -> `ProviderProfile`

Why:
- Routing layer stays provider-neutral.
- Model catalog can change without touching route logic.
- Prevents leaking provider details into upper layers.

---

## 6) Security Boundaries in Plain Language

1. Route decision has no secrets.
2. Prompt resolver controls prompt file paths.
3. Query/context stay in user message and do not enter public result.
4. Public output (`OrchestrationResult`) is sanitized.
5. Metadata is blocked from including secret-like keys.
6. No env var values or cloud secret reads in this layer.

---

## 7) Performance Design in Plain Language

1. YAML parse happens once at startup/singleton creation.
2. Request-time routing is dictionary lookup.
3. Prompt files are cached in memory.
4. Part 4 resolution is map lookup + validation only.
5. No network and no AWS calls in these foundation parts.

---

## 8) Common Confusions (Quick Clarification)

### "Why both ModelExecutor and ProviderExecutor?"
- `ModelExecutor` is orchestrator-facing boundary.
- `ProviderExecutor` is lower-level provider-facing boundary.
- `RegistryBackedModelExecutor` bridges them.

### "Why not use model_router.py directly now?"
- Current `model_router.py` uses role-based env config (`LlmRoleConfig`), not route alias + registry metadata path.
- Forcing it now would couple unrelated layers.

### "Where is fallback execution?"
- Not implemented yet by design.
- `fallback_attempts` is currently metadata from routing.

---

## 9) What Is Deferred to Later Parts

- Real provider adapters (OpenAI/Azure/Gemini SDK calls).
- Secret resolver (env/credentials/manager integration).
- Graph wiring into runtime flow.
- Actual fallback execution orchestration.
- Langfuse/config bundle prompt sources.

---

## 10) Learning Checklist (Use This to Study)

1. Read how `RouteRequest` becomes `RouteDecision`.
2. Read how `RouteDecision` becomes 2 `LlmMessage` entries.
3. Read how model alias resolves to `ResolvedModelConfig`.
4. Trace how `ProviderExecutionRequest` is created.
5. Confirm what is included/excluded in `OrchestrationResult`.
6. Inspect validators that block unsafe metadata.
7. Inspect logs to see safe observability fields only.

If you want, next I can add a second file with line-by-line walkthrough for one concrete request example (for example: math/generator/basic with a sample query).