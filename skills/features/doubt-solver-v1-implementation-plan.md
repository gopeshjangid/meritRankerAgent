# Implementation Plan: Doubt Solver V1

> Role: Solution Architect
> Template: `skills/templates/implementation-plan-template.md`
> Feature: `skills/features/doubt-solver.md`
> BA Requirements: `skills/features/doubt-solver-v1-ba-requirements.md`
> Date: 2026-05-23

---

## Goal

Add a Doubt Solver graph, schemas, and services to the existing `app/` that accepts
a student query, classifies it, generates an answer through a service boundary, validates
the output, and returns a structured JSON response — all without touching the demo graph,
without adding any infrastructure, and with all tests runnable offline.

---

## Non-Goals

- No DynamoDB, no Bedrock KB, no retrieval of any kind.
- No streaming.
- No Redis, no cache.
- No tools, no memory.
- No production auth.
- No changes to `agentcore/`.
- No changes to the existing demo graph or demo schemas.
- No change to `AgentRequest` or `AgentResponse` public schemas (preserved as-is).

---

## Current Context

| Component | Current state |
|---|---|
| `app/main.py` | Exists. Routes all requests through `demo_graph`. Must stay thin. |
| `app/graphs/demo_graph.py` | Exists. Two nodes. Do not modify. |
| `app/schemas/request.py` | Exists. `AgentRequest`. Do not modify existing fields. |
| `app/schemas/response.py` | Exists. `AgentResponse`. Do not modify. |
| `app/services/mock_response_service.py` | Exists. Will be reused as fallback generator. |
| `skills/features/doubt-solver.md` | Exists. Planned status. Update after implementation. |

---

## Architecture Decision

Route on `mode` value at the entrypoint. `app/main.py` selects the graph based on
`payload["mode"]`. This keeps each graph self-contained and avoids modifying existing graphs.

**Decision:** `main.py` reads `mode` from the validated request and calls
`build_doubt_solver_graph()` when `mode == "doubt_solver"`, otherwise falls back to
the demo graph.

**[REQUIRES ARCHITECT ALIGNMENT]** Any change to `main.py` routing must not break
existing demo graph tests or the public `AgentRequest`/`AgentResponse` contract.

---

## Files to Add / Change

| File | Action | Description |
|---|---|---|
| `app/main.py` | Modify | Add mode-based graph routing (thin — 3–5 lines) |
| `app/graphs/doubt_solver_graph.py` | New | 3-node graph: classify → generate → validate_and_respond |
| `app/schemas/doubt_solver.py` | New | `DoubtSolverRequest`, `DoubtSolverResponse`, `QueryClassificationResult`, `GeneratedAnswer` |
| `app/services/query_classifier_service.py` | New | Stub classifier — returns `QueryClassificationResult` |
| `app/services/answer_generator_service.py` | New | Wraps mock (or real LLM later) — returns `GeneratedAnswer` |
| `app/prompts/doubt_solver.md` | New | Placeholder prompt template for answer generator |
| `app/prompts/query_classifier.md` | New | Placeholder prompt template for classifier |
| `app/tests/test_doubt_solver_schemas.py` | New | Schema validation tests |
| `app/tests/test_doubt_solver_graph.py` | New | Graph flow tests with mocked services |
| `skills/features/doubt-solver.md` | Update | Reflect V1 In Progress / Implemented status |

---

## Data Flow

```
POST /invocations  (AgentCore)
  → main.py: invoke(payload)
    → AgentRequest.model_validate(payload)          # existing validation
    → if mode == "doubt_solver":
        graph = build_doubt_solver_graph()
      else:
        graph = build_demo_graph()
    → graph.invoke(state_dict)
      → classify_node:
          calls query_classifier_service.classify(message)
          writes QueryClassificationResult to state
      → generate_node:
          reads classification from state
          calls answer_generator_service.generate(message, classification)
          writes GeneratedAnswer to state
      → respond_node:
          validates GeneratedAnswer schema (already validated by service)
          builds DoubtSolverResponse
          on validation failure → fallback DoubtSolverResponse(success=False)
    → AgentResponse.model_dump()                    # existing response wrapper
  → HTTP response
```

**Note:** `AgentResponse` wraps the inner answer string as before.
`classification` and Doubt Solver-specific fields live in the internal state and
service schemas — they are not added to the public `AgentResponse` in V1.

> [ASSUMPTION] Keeping `AgentResponse` unchanged for V1 avoids a breaking schema change.
> If `classification` must surface in the API response, this is a V2 schema decision
> requiring explicit discussion. Do not implement without approval.

---

## Service Boundaries

| Integration | Service file | V1 implementation |
|---|---|---|
| Query classification | `app/services/query_classifier_service.py` | Stub — returns fixed `QueryClassificationResult` based on simple keyword match or always returns `unknown` |
| Answer generation | `app/services/answer_generator_service.py` | Wraps `mock_response_service.generate_mock_response()` for V1; swap for real LLM later |

**Rule:** Graph nodes call services only. No `boto3`, `anthropic`, or provider SDK imports
in any graph node or tool file. See `skills/core/integration-boundaries.md`.

---

## Schema / Contract Changes

| Schema | Field | Change type | Backward-compatible? |
|---|---|---|---|
| `AgentRequest` | — | None | Yes — unchanged |
| `AgentResponse` | — | None | Yes — unchanged |
| `DoubtSolverRequest` | New model | New | N/A — new |
| `DoubtSolverResponse` | New model | New | N/A — new |
| `QueryClassificationResult` | New model | New | N/A — new |
| `GeneratedAnswer` | New model | New | N/A — new |

No breaking changes to public API. `AgentRequest`/`AgentResponse` are preserved as-is.

### `DoubtSolverRequest` fields

| Field | Type | Constraints |
|---|---|---|
| `message` | `str` | min 1, max 2000, whitespace stripped |
| `user_id` | `str` | min 1, max 128 |
| `mode` | `Literal["doubt_solver"]` | exact value |

### `QueryClassificationResult` fields

| Field | Type | Notes |
|---|---|---|
| `subject` | `str` | e.g. `"math"`, `"unknown"` |
| `intent` | `str` | e.g. `"solve_question"`, `"explain_concept"`, `"unknown"` |
| `response_style` | `str` | e.g. `"step_by_step"`, `"short_answer"`, `"unknown"` |

> [ASSUMPTION] V1 classifier stub returns `"unknown"` for all dimensions by default,
> upgraded by keyword matching or fixed mapping later.

### `GeneratedAnswer` fields

| Field | Type | Constraints |
|---|---|---|
| `text` | `str` | min 1, max 10000 chars |
| `is_fallback` | `bool` | `True` if classifier returned `unknown` for all dimensions |

---

## Config / Env Changes

No new env vars required for V1 (mock services only).

When a real LLM is added later, add:
- `MODEL_PROVIDER` — already exists, currently `mock`
- `GENERATOR_MODEL_ID` — Bedrock model ID for answer generation

No new env vars in V1.

---

## Testing Plan

| Scenario | File | Test name | Type |
|---|---|---|---|
| Valid `DoubtSolverRequest` accepted | `test_doubt_solver_schemas.py` | `test_valid_request` | Unit |
| Empty message rejected | `test_doubt_solver_schemas.py` | `test_empty_message_rejected` | Unit |
| Message over max length rejected | `test_doubt_solver_schemas.py` | `test_message_too_long_rejected` | Unit |
| Response fields always present | `test_doubt_solver_schemas.py` | `test_response_fields_present` | Unit |
| Graph runs classify then generate | `test_doubt_solver_graph.py` | `test_graph_classifies_then_generates` | Graph |
| Unknown classification → fallback answer | `test_doubt_solver_graph.py` | `test_unknown_query_returns_fallback` | Graph |
| Invalid model output → graceful error | `test_doubt_solver_graph.py` | `test_invalid_model_output_returns_error` | Graph |
| `mode=doubt_solver` reaches correct graph | `test_doubt_solver_graph.py` | `test_mode_routing` | Integration |
| Demo graph still passes after routing change | `test_demo_graph.py` | (existing — must still pass) | Regression |

All tests must pass offline. No real LLM, no AWS, no network.

---

## Security Notes

| Concern | Assessment |
|---|---|
| Input validation | Pydantic at entrypoint — existing pattern |
| Model output trust | `GeneratedAnswer.model_validate()` in service before use — required [AI RISK] |
| Logging | No full `message` or `answer` text at INFO level |
| Auth | [AUTH TODO] — not implemented, demo only [PROD BLOCKER] |
| Secrets | None added in V1 |

---

## Performance / Cost Notes

| Concern | Assessment |
|---|---|
| Model calls per request | 1 (answer generation only) — V1 classifier is a stub, not a model call |
| External calls | 0 in V1 (all mocked) |
| Prompt size | Bounded by `max_length=2000` on input field |

---

## Risks

| Risk | Likelihood | Impact | Label | Mitigation |
|---|---|---|---|---|
| `main.py` routing change breaks demo graph tests | Low | High | | Add regression tests for demo graph before merging |
| `GeneratedAnswer` validation schema too strict, rejects valid LLM output | Medium | Medium | [AI RISK] | Design schema with reasonable `max_length` and loose text constraints |
| V1 stub classifier makes feature appear non-functional | Low | Low | [ASSUMPTION] | Document stub status in response; easy swap in V2 |

---

## Rollback / Disable Plan

- Set `mode` to anything other than `"doubt_solver"` to route to demo graph.
- The Doubt Solver graph can be removed without touching the demo graph or public schema.
- No infrastructure to roll back.

---

## Acceptance Criteria

- [ ] All BA acceptance criteria AC-01 through AC-12 are met.
- [ ] `make check` passes (0 ruff errors, all tests green including existing 17).
- [ ] `agentcore validate` passes.
- [ ] `demo_graph` tests still pass after `main.py` routing change.
- [ ] No secrets hardcoded.
- [ ] `skills/features/doubt-solver.md` updated to `In Progress` or `Local Demo`.

---

## Handoff to Engineer

**Approved by:** Solution Architect (self-reviewed)
**Date:** 2026-05-23

**Start with:** `app/schemas/doubt_solver.py` — define all four Pydantic models first.
Then services, then graph, then routing change in `main.py` last (after tests pass for
graph in isolation).

**Known unknowns — flag if blocked:**
- If real LLM is available, confirm with architect before wiring it in V1.
- If `main.py` routing change causes test failures, stop and escalate before continuing.

**Out of bounds — do not implement:**
- No DynamoDB. No Bedrock KB. No tools. No streaming. No Redis. No auth.
- Do not modify `AgentRequest`, `AgentResponse`, or the demo graph.
