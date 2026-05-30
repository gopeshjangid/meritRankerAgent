# BA Requirements: Doubt Solver V1

> Role: Business Analyst
> Template: `skills/templates/ba-requirements-template.md`
> Feature: `skills/features/doubt-solver.md`
> Product Brief: `skills/features/doubt-solver-v1-product-brief.md`
> Date: 2026-05-23

---

## Requirement Summary

The Doubt Solver V1 accepts a student's text query, classifies it by subject and intent,
generates a helpful explanation through a controlled LLM service boundary, validates the
structured output, and returns a synchronous JSON response. V1 uses stubbed/mock services.
No retrieval, no storage, no streaming.

---

## Actors / Users

| Actor | Role | Interaction |
|---|---|---|
| Student | Primary user | Sends a text doubt/question; receives an explanation |
| System | Automated | Validates, classifies, generates, validates output, returns response |

---

## Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | The system SHALL accept a text query from the student. | Must |
| FR-02 | The system SHALL reject empty or whitespace-only queries with a validation error. | Must |
| FR-03 | The system SHALL reject queries exceeding the maximum length with a validation error. | Must |
| FR-04 | The system SHALL classify the query by subject and intent before generating an answer. | Must |
| FR-05 | The system SHALL generate an answer via a service boundary (no direct model calls from graph nodes). | Must |
| FR-06 | The system SHALL validate the structure of the generated answer before returning it to the caller. | Must |
| FR-07 | The system SHALL return a structured JSON response containing `success`, `answer`, `request_id`, `mode`, and `classification`. | Must |
| FR-08 | The system SHALL return a safe fallback response when the query type is unknown or classification confidence is insufficient. | Must |
| FR-09 | The system SHALL return a graceful error response (not a crash or unhandled exception) if model output fails validation. | Must |
| FR-10 | The system SHALL route `mode="doubt_solver"` requests to the Doubt Solver graph. | Must |
| FR-11 | Tests SHALL NOT require a real LLM, real AWS credentials, or network access. | Must |

---

## Input / Output Specification

### Input — `DoubtSolverRequest`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `message` | `str` | Yes | min 1 char, max 2000 chars, whitespace stripped |
| `user_id` | `str` | Yes | min 1 char, max 128 chars |
| `mode` | `str` | Yes | must equal `"doubt_solver"` for this graph |

> [ASSUMPTION] Max message length is 2000 chars for V1. SA to confirm.
> [ASSUMPTION] `mode` field is used for routing — exact routing mechanism per SA.

### Output — `DoubtSolverResponse`

| Field | Type | Always present | Notes |
|---|---|---|---|
| `success` | `bool` | Yes | `True` on valid answer, `False` on error |
| `request_id` | `str` | Yes | UUID, generated at entrypoint |
| `mode` | `str` | Yes | Echoes `"doubt_solver"` |
| `answer` | `str \| None` | On success | The generated explanation |
| `classification` | `dict \| None` | On success | Subject and intent from classifier |
| `error` | `str \| None` | On failure | Human-readable error message |

> [NOT VERIFIED] `classification` field structure — AI Architect to define schema.

---

## User Scenarios

**Scenario 1 — Happy path: solve question**
> Student sends "What is 20% of 500?" with `mode="doubt_solver"`.
> System classifies: subject=math, intent=solve_question.
> System generates: "20% of 500 = 100. To find 20%, multiply 500 by 0.20..."
> Student receives `success=True`, `answer="20% of 500 = 100..."`, `classification`.

**Scenario 2 — Happy path: explain concept**
> Student sends "Explain what ratio means." with `mode="doubt_solver"`.
> System classifies: subject=math, intent=explain_concept.
> System generates a plain-language explanation.
> Student receives `success=True`, `answer="A ratio compares two quantities..."`.

**Scenario 3 — Unknown query type**
> Student sends "asdkjhaskdjh" (gibberish).
> System classifies: subject=unknown, intent=unknown.
> System returns fallback: `success=True`, `answer="I'm not sure what you're asking. Could you rephrase?"`.

**Scenario 4 — Empty message**
> Student sends `message=""`.
> System returns validation error before reaching the graph: `success=False`, `error="message: min length 1"`.

**Scenario 5 — Model output validation failure**
> LLM service returns malformed output.
> System catches `ValidationError`, logs at WARNING, returns: `success=False`, `error="Could not generate answer. Please try again."`.

---

## Edge Cases

| Edge Case | Expected Behaviour |
|---|---|
| Empty string message | Validation error — FR-02 |
| Whitespace-only message | Validation error after stripping — FR-02 |
| Message exactly at max length (2000 chars) | Accepted and processed |
| Message one char over max length (2001 chars) | Validation error — FR-03 |
| `user_id` empty string | Validation error |
| `mode` value other than `"doubt_solver"` | Routed to demo graph or returns error — SA to define |
| Classifier returns `unknown` for all dimensions | Fallback answer returned — FR-08 |
| Model service returns empty string | Caught by output validation, graceful error — FR-09 |
| Model service raises exception | Caught at entrypoint, `success=False` returned — FR-09 |
| Very long answer from model (>10k chars) | [NOT VERIFIED] — SA should define max output length |

---

## Acceptance Criteria

| ID | Criterion | Linked FR |
|---|---|---|
| AC-01 | `DoubtSolverRequest` with valid `message`, `user_id`, `mode` is accepted. | FR-01 |
| AC-02 | `DoubtSolverRequest` with `message=""` raises `ValidationError`. | FR-02 |
| AC-03 | `DoubtSolverRequest` with `message` of 2001 chars raises `ValidationError`. | FR-03 |
| AC-04 | Graph runs classifier node before answer generation node. | FR-04 |
| AC-05 | Classifier result is written to state and passed to answer generation node. | FR-04, FR-05 |
| AC-06 | Answer generator node calls service, not a model SDK directly. | FR-05 |
| AC-07 | `GeneratedAnswer` Pydantic schema validation runs before state is updated. | FR-06 |
| AC-08 | Response always contains `success`, `answer`, `request_id`, `mode`. | FR-07 |
| AC-09 | Unknown classification returns fallback answer, not an error. | FR-08 |
| AC-10 | Malformed model output returns `success=False` with a user-safe error string. | FR-09 |
| AC-11 | `mode="doubt_solver"` request reaches Doubt Solver graph, not demo graph. | FR-10 |
| AC-12 | All tests pass with mocked services, no real LLM or AWS calls. | FR-11 |

---

## Requirement-to-Test Mapping

| Requirement | Test File | Test Name | Status |
|---|---|---|---|
| FR-01, FR-02, FR-03 | `app/tests/test_doubt_solver_schemas.py` | `test_valid_request`, `test_empty_message`, `test_message_too_long` | Planned |
| FR-04, FR-05 | `app/tests/test_doubt_solver_graph.py` | `test_graph_classifies_then_generates` | Planned |
| FR-06, FR-09 | `app/tests/test_doubt_solver_graph.py` | `test_invalid_model_output_returns_error` | Planned |
| FR-07 | `app/tests/test_doubt_solver_schemas.py` | `test_response_fields_present` | Planned |
| FR-08 | `app/tests/test_doubt_solver_graph.py` | `test_unknown_query_returns_fallback` | Planned |
| FR-10 | `app/tests/test_doubt_solver_graph.py` | `test_mode_routing` | Planned |
| FR-11 | All test files | (all) | Planned — no real calls |

---

## Non-Goals

- No retrieval — no KB or DynamoDB calls.
- No streaming.
- No session memory.
- No tools.
- No production auth.
- No subject-specific routing to expert agents.
- No answer accuracy evaluation in V1.

---

## Data Sensitivity Notes

| Data Field | Sensitivity | Handling |
|---|---|---|
| `message` | Potentially sensitive student content | Do not log full content at INFO level |
| `user_id` | Student identifier | Do not expose in error messages |
| `answer` | Generated content | Do not log full text at INFO level |

---

## Dependency Failure Expectations

| Service | Failure Mode | Expected Behaviour |
|---|---|---|
| Classifier service | Returns `unknown` values | Fallback answer path — not an error |
| Answer generator service | Raises exception | Caught at entrypoint, `success=False` |
| Answer generator service | Returns malformed output | `ValidationError` caught at node, `success=False` |

---

## Open Questions

| # | Question | Status |
|---|---|---|
| 1 | Does `main.py` route by `mode` value, or does the graph handle routing internally? | Open — SA to decide |
| 2 | What is the max safe answer length (chars/tokens) to bound output? | Open — SA/AI Arch to decide |
| 3 | Should `classification` appear in the V1 response, or only internally? | Open — PM to confirm |

---

## Assumptions

| # | Assumption | Label |
|---|---|---|
| 1 | V1 classifier is a mock/stub — no real model call | [ASSUMPTION] |
| 2 | V1 answer generator may be mock or real LLM depending on readiness | [ASSUMPTION] |
| 3 | Max message length 2000 chars is appropriate for V1 | [ASSUMPTION] |
| 4 | `mode="doubt_solver"` is the routing key | [ASSUMPTION] |

---

## Blockers

None at BA stage. All blockers are open questions resolved by SA/AI Architect.
