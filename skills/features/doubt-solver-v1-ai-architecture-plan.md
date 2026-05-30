# AI Architecture Plan: Doubt Solver V1

> Role: AI Solution Architect
> Template: `skills/templates/ai-architecture-plan-template.md`
> Feature: `skills/features/doubt-solver.md`
> Implementation Plan: `skills/features/doubt-solver-v1-implementation-plan.md`
> Date: 2026-05-23

---

## AI Workflow Plan

V1 is a 3-step synchronous pipeline:

1. **Classify** — A stub/keyword classifier determines `subject`, `intent`, and
   `response_style` from the student message. No real model call in V1.
2. **Generate** — An answer generator service receives the message and classification
   result, builds a prompt, and calls the LLM (or mock) through a service boundary.
3. **Validate and respond** — The generated output is schema-validated before being
   returned. On validation failure, a safe fallback response is returned.

No retrieval. No tools. No streaming. One model call maximum.

---

## Graph Design

| Node | Type | Purpose |
|---|---|---|
| `classify_node` | Standard | Calls `query_classifier_service.classify(message)`, writes `QueryClassificationResult` to state |
| `generate_node` | Standard | Calls `answer_generator_service.generate(message, classification)`, writes `GeneratedAnswer` to state |
| `respond_node` | Standard | Reads validated `GeneratedAnswer` from state, builds final response |

**Edges:**

```
START → classify_node → generate_node → respond_node → END
```

**No conditional routing in V1.** Linear graph only.

If `classification.subject == "unknown"` and `classification.intent == "unknown"`,
the answer generator service returns a fallback `GeneratedAnswer` with `is_fallback=True`.
The graph does not branch — the fallback is handled inside the generator service.

> [AI RISK] Conditional routing based on classifier output is deferred to V2 deliberately.
> V1 linear graph eliminates model-driven routing risks.

---

## Prompt / Model / Retrieval Boundaries

| Step | Type | Model / Source | Input | Output | Boundary |
|---|---|---|---|---|---|
| `classify_node` | Stub (V1) | Keyword match / always-unknown | `message` string | `QueryClassificationResult` | `app/services/query_classifier_service.py` |
| `generate_node` | LLM or mock | `mock_response_service` (V1) / Bedrock (V2) | `message` + `classification` | `GeneratedAnswer` | `app/services/answer_generator_service.py` |

**Why no real classifier in V1:**
A real classifier model call adds latency, cost, and a second AI failure mode on the
critical path. V1 validates the pipeline structure — a stub classifier is sufficient
to confirm the graph flows correctly. Real classification is a V2 concern.

**Why no real LLM required for V1 tests:**
Tests must run offline. The service layer is mockable — the graph is tested with
a service mock, not a real model. If a real LLM is available for local dev, it can be
wired through `answer_generator_service.py` without changing the graph.

**[AI RISK]** All model output is untrusted until `GeneratedAnswer.model_validate()` runs
inside `answer_generator_service.py`. The node never acts on raw model text.

---

## Tool Boundaries

No tools in V1. `app/tools/` is not used.

LangGraph `ToolNode` is not added. Tools require additional fallback handling, retry logic,
and output validation surfaces — deferred to V2 when justified by a specific use case.

**[REQUIRES ARCHITECT ALIGNMENT]** Any V2 tool addition must be reviewed by AI Solution
Architect before implementation.

---

## State / Schema Additions

### `DoubtSolverGraphState` (TypedDict)

| Field | Type | Set by |
|---|---|---|
| `request_id` | `str` | `main.py` before graph |
| `message` | `str` | `main.py` before graph |
| `user_id` | `str` | `main.py` before graph |
| `mode` | `str` | `main.py` before graph |
| `classification` | `QueryClassificationResult \| None` | `classify_node` |
| `generated_answer` | `GeneratedAnswer \| None` | `generate_node` |
| `error` | `str \| None` | `respond_node` on failure |

**Rule:** State fields hold validated Pydantic model instances, not raw model text.
Raw text never appears in state.

---

## Hallucination Risks

| Risk | Mitigation | Label |
|---|---|---|
| Model generates incorrect maths answer | V1 has no answer verification — documented as known limitation | [AI RISK] |
| Model generates an answer for an unsupported topic and presents it confidently | `is_fallback=True` flag in `GeneratedAnswer` allows caller to surface appropriate UX | [AI RISK] |
| Model generates a very long response that floods state/response | `GeneratedAnswer.text` has `max_length=10000` constraint | [AI RISK] |
| Model returns an empty string | Caught by `min_length=1` constraint on `GeneratedAnswer.text` | [AI RISK] |

---

## Prompt-Injection Risks

V1 uses a single user-controlled field (`message`) as model input.

| Prompt section | Content source | Injection risk | Mitigation |
|---|---|---|---|
| System role | Hard-coded in `doubt_solver.md` prompt template | Low | User content never placed in system role |
| User turn | Student `message` field | Medium | Bounded by `max_length=2000` in schema; placed in clearly delimited user section |

No retrieved content in V1. Retrieved content injection risk is a V2 concern.

**Prompt design rule:** The system prompt must instruct the model to act as a tutoring
assistant and to decline to answer requests that are off-topic or harmful. The `message`
field is placed in the user turn only — never in the system prompt.

---

## Output Validation Strategy

| Node | Service output type | Validation method | On failure |
|---|---|---|---|
| `classify_node` | `QueryClassificationResult` | `model_validate()` inside `query_classifier_service` | Returns `QueryClassificationResult` with all fields `"unknown"` — no exception |
| `generate_node` | `GeneratedAnswer` | `model_validate()` inside `answer_generator_service` | Raises `AnswerGenerationError` (domain exception) |
| `respond_node` | (reads validated state) | No re-validation — trusts service output | Catches `AnswerGenerationError`, returns `success=False` |

**Rule:** Services absorb provider-specific exceptions and raise a single domain exception
type. Graph nodes catch that domain exception and convert it to a response — they do not
import or handle provider-specific errors.

---

## Evaluation / Test Strategy

| Test | File | Type | Mock |
|---|---|---|---|
| Graph produces answer for valid input | `test_doubt_solver_graph.py` | Graph | `monkeypatch` classifier + generator services |
| Unknown classification returns fallback | `test_doubt_solver_graph.py` | Graph | Classifier returns all-`unknown` stub |
| Invalid model output returns graceful error | `test_doubt_solver_graph.py` | Graph | Generator service returns invalid format |
| Generator service exception returns `success=False` | `test_doubt_solver_graph.py` | Graph | Generator raises `AnswerGenerationError` |
| Schema: empty message rejected | `test_doubt_solver_schemas.py` | Unit | None needed |
| Schema: max-length message accepted | `test_doubt_solver_schemas.py` | Unit | None needed |
| Schema: `GeneratedAnswer` empty text rejected | `test_doubt_solver_schemas.py` | Unit | None needed |

**[NOT VERIFIED]** No evaluation against real LLM output has been run —
V1 tests use mocks only.

---

## Model / Provider Requirements

| Requirement | V1 value | Status |
|---|---|---|
| Model provider | `mock` (V1) / Bedrock (V2) | V1: mock sufficient |
| Classifier model | Stub (V1) | No model needed for V1 |
| Generator model | `mock_response_service` or any Bedrock text model | [ASSUMPTION] — Bedrock not wired in V1 |
| Context window | Not critical for V1 (stub + short messages) | [ASSUMPTION] |
| Tool-calling support | Not needed — V1 has no tools | N/A |

---

## Latency / Cost Notes

| Factor | V1 value | Label |
|---|---|---|
| Model calls per request | 0 (mock) or 1 (if real LLM wired) | Acceptable |
| Classifier calls | 0 (stub — CPU only) | Acceptable |
| Retrieval calls | 0 | N/A — no retrieval in V1 |
| Prompt tokens per request | ~200–500 (short message + system prompt) | [ASSUMPTION] |
| User-facing latency | <100ms with mock; <5s with real LLM | [ASSUMPTION] |

---

## Observability Plan

| Signal | Implementation | Status |
|---|---|---|
| Classification result | Logged at DEBUG level in `classify_node` | Planned |
| Generation success/failure | Logged at INFO/WARNING in `generate_node` | Planned |
| Validation failure | Logged at WARNING in `answer_generator_service` | Planned |
| Per-node latency | Not implemented in V1 | [DEFER] — V2 |

---

## Clarification / Escalation Plan

- If the stub classifier is insufficient to demonstrate the feature to stakeholders,
  escalate to PM before adding a real classifier. Do not add a real model call without
  a new AI Architecture review.
- If model output consistently fails `GeneratedAnswer` validation, escalate to AI
  Solution Architect before relaxing schema constraints.
- If prompt injection is identified in test or review, escalate to Security Reviewer
  before release.
- **[REQUIRES ARCHITECT ALIGNMENT]** Any V1 extension (retrieval, streaming, tools)
  requires a new plan — do not implement in the same PR.

---

## Open Issues

| # | Issue | Label | Status |
|---|---|---|---|
| 1 | Real classifier not defined for V1 — stub is sufficient | [ASSUMPTION] | Accepted |
| 2 | Real LLM not wired in V1 — mock is sufficient for pipeline validation | [ASSUMPTION] | Accepted |
| 3 | `GeneratedAnswer.text` max_length=10000 not confirmed against model behaviour | [NOT VERIFIED] | Open |
| 4 | V1 has no answer accuracy evaluation — this is documented as a known limitation | [AI RISK] | Deferred to V2 |

---

## Why Each V1 Constraint Exists

| Constraint | Reason |
|---|---|
| No real LLM required | Tests must run offline. Mock is sufficient to validate pipeline structure. |
| No retrieval | Retrieval adds a second failure mode, latency, and prompt injection surface. V1 validates the classify-generate-validate pattern first. |
| No streaming | Streaming changes the response contract significantly. V1 validates synchronous JSON first. |
| No tools | Tools add LangGraph `ToolNode`, retry logic, and additional output validation surfaces. Not justified before the base pipeline is validated. |
| Linear graph (no conditional routing) | Model-driven routing in V1 would require the classifier to be reliable enough to route safely. V1 stub classifier is not. |
| Stub classifier | A real classifier model call is a second AI failure mode on the critical path. V1 deliberately tests one AI boundary at a time. |
