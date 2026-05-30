# Feature: Demo Agent

> Context file for the local AgentCore + LangGraph foundation.
> Update this file whenever the demo feature changes.

---

## Purpose

Proves that the local development stack works end-to-end:

- AgentCore runtime accepts HTTP requests via `BedrockAgentCoreApp`.
- LangGraph `StateGraph` executes a two-node workflow.
- Pydantic v2 validates inbound and outbound payloads.
- Rich logging produces readable output during `make dev`.
- Tests cover schema validation and graph execution without AWS credentials.

This is a **foundation only** — no real LLM, no storage, no auth.

---

## Current Status

**Demo** — local dev foundation.  Not connected to any real model or data store.

---

## Entrypoints

| File | Function | Description |
|---|---|---|
| `app/main.py` | `invoke(payload: dict) -> dict` | Single AgentCore entrypoint for all requests |

**Flow:**
```
POST /invocations
  → invoke()
    → AgentRequest.model_validate(payload)
    → graph.invoke(state_dict)
    → AgentResponse.model_dump()
  → HTTP response
```

---

## Graphs

| File | Builder | Nodes |
|---|---|---|
| `app/graphs/demo_graph.py` | `build_demo_graph()` | `start_node` → `respond_node` |

**Node descriptions:**

| Node | Behaviour |
|---|---|
| `start_node` | Logs `request_id`, `user_id`, `mode`.  No state mutation. |
| `respond_node` | Calls `generate_mock_response(message)`, writes `answer` to state. |

**Internal state type:** `DemoGraphState` (TypedDict)

---

## Schemas

| File | Model | Purpose |
|---|---|---|
| `app/schemas/request.py` | `AgentRequest` | Validates inbound HTTP payload |
| `app/schemas/response.py` | `AgentResponse` | Structures outbound response |
| `app/schemas/state.py` | `AgentState` | Python-layer graph state (Pydantic wrapper) |

**AgentRequest fields:**

| Field | Type | Default | Constraint |
|---|---|---|---|
| `message` | `str` | required | 1–5000 chars, whitespace stripped |
| `user_id` | `str` | `"local-user"` | 1–128 chars |
| `mode` | `str` | `"demo"` | 1–64 chars |

**AgentResponse fields:** `success`, `answer`, `request_id`, `mode`

---

## Services

| File | Function | Description |
|---|---|---|
| `app/services/mock_response_service.py` | `generate_mock_response(message)` | Returns a canned string.  Swap for real LLM later. |

---

## Tools

None — no LangGraph tools are used in the demo workflow.

---

## Prompts

| File | Use |
|---|---|
| `app/prompts/demo.md` | Placeholder — reserved for future real prompt templates |

---

## Tests

| File | Covers |
|---|---|
| `app/tests/test_schemas.py` | `AgentRequest` validation (valid, empty, too-long, whitespace) |
| `app/tests/test_schemas.py` | `AgentResponse` serialisation |
| `app/tests/test_schemas.py` | `AgentState` construction |
| `app/tests/test_demo_graph.py` | Graph compiles and returns a compiled graph |
| `app/tests/test_demo_graph.py` | Graph produces a non-empty answer |
| `app/tests/test_demo_graph.py` | Answer contains the original message text |
| `app/tests/test_demo_graph.py` | `request_id` is preserved through the graph |
| `app/tests/test_demo_graph.py` | Graph is reusable across multiple calls |

**Test count:** 17 tests, all passing as of initial setup.

---

## Config / Env

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `local` | Environment tag used for logging |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MODEL_PROVIDER` | `mock` | Which response service to use (`mock` only currently) |

Set in `app/.env.local` (copy from `app/.env.local.example`).

---

## Known Limitations

- **No real LLM** — response is a hardcoded echo string.
- **No storage** — no session history, no user profile persistence.
- **No external search** — no retrieval-augmented generation.
- **No authentication** — requests are not authenticated or authorised.
- **Single mode** — `mode` field accepted but not acted on differently.
- **No streaming** — response is returned as a single synchronous dict.

---

## Latest Changes

- `2026-05-23` — Feature context updated: README.md table updated, doubt-solver.md added as planned feature.
- `2026-05-20` — Initial foundation created.  Two-node demo graph, Pydantic schemas,
  Rich logging, mock response service, 17 pytest tests, ruff lint passing.

---

## Next Steps

- [ ] Keep this demo graph stable — do not mix Doubt Solver logic into the demo graph.
- [ ] Add real LLM service (Bedrock / Anthropic) behind `MODEL_PROVIDER` env var.
- [ ] Add `mode`-based routing in the graph (e.g., `demo` vs `doubt_solver`).
- [ ] Run PM → BA → Architect planning for Doubt Solver before implementing it.
- [ ] Add request authentication middleware (see `skills/core/security-and-privacy.md`).
- [ ] Add streaming response support (deferred to later phase).
