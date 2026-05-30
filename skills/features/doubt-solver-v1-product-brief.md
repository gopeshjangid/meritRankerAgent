# Product Brief: Doubt Solver V1

> Role: Product Manager
> Template: `skills/templates/product-brief-template.md`
> Feature: `skills/features/doubt-solver.md`
> Date: 2026-05-23

---

## Product Stage

Foundation Demo → V1 Feature

---

## User Problem

Students preparing for competitive exams (e.g., banking, SSC, UPSC) encounter questions
and concepts they don't understand. They need an immediate, clear explanation — like a
patient tutor who can understand the type of question, identify what the student needs
(solution, concept explanation, hint, step-by-step walkthrough), and respond accordingly.

Current state: no such automated tutoring exists in MeritRanker Tutor.
The demo agent returns only a mock echo response — it does not help any student.

---

## Target User

Secondary or graduate-level student preparing for a competitive entrance exam.
Not technical. Expects a clear, contextual answer in plain language.

---

## Pain Severity

**High.** Students encounter blockers mid-study session. Waiting for manual help
breaks learning momentum. The gap between "I'm stuck" and "I understand" is the core
product problem.

---

## Why Now

The demo agent foundation (AgentCore + LangGraph + Pydantic) is stable.
V1 is the first step from a working skeleton to a working product.
V1 is intentionally minimal so the team can validate the end-to-end pipeline
(classification → generation → validated response) before adding retrieval, streaming,
and personalisation.

---

## User Flow

1. Student types a doubt or question into the interface.
2. Student submits — system receives a JSON payload with `message`, `user_id`, `mode`.
3. System validates input (length, required fields).
4. System classifies the query (subject, intent, response style).
5. System generates a helpful explanation using an LLM through a service boundary.
6. System validates the model output structure.
7. Student receives a structured JSON response with the answer.

---

## MVP Scope

- [x] Accept text query from student via existing `AgentRequest` or a new `DoubtSolverRequest`.
- [x] Validate input (Pydantic, existing rules).
- [x] Classify query: subject, intent, response style — using a stubbed/mock classifier for V1.
- [x] Generate answer using LLM (via `mock_response_service` for V1 or real LLM if ready).
- [x] Validate model output structure before returning.
- [x] Return structured JSON response.
- [x] New LangGraph graph: `doubt_solver_graph.py`.
- [x] New Pydantic schemas: `DoubtSolverRequest`, `DoubtSolverResponse`, `QueryClassificationResult`, `GeneratedAnswer`.
- [x] Classification service and answer generation service behind service boundary.
- [x] Tests: schema validation, graph flow with mocks, classification stub, validation failure.

---

## Non-Goals (V1 Strict)

- No DynamoDB — no persistent storage.
- No Bedrock Knowledge Base — no retrieval.
- No streaming — synchronous JSON response only.
- No Redis / cache.
- No memory — no session history.
- No tools — no LangGraph tool nodes.
- No real retrieval or context injection.
- No subject-specific expert agents.
- No advanced answer verification pipeline.
- No production authentication.
- No audio, image, OCR, or multimodal input.
- No long-term student profile or personalisation.

---

## Success Metrics

| Metric | V1 Target | Measurement Method |
|---|---|---|
| End-to-end request succeeds | 100% for valid inputs | pytest + manual local test |
| Classification returns a valid result | 100% with mock classifier | pytest |
| Malformed model output is caught | 100% | pytest (mock bad output) |
| `make check` passes | 0 errors, all tests green | CI gate |
| `agentcore validate` passes | Valid | CLI |
| Fallback response on unknown query | Graceful, not a 500 | pytest |

---

## User-Facing Acceptance Criteria

- [ ] Given a valid doubt text, the system returns a structured answer.
- [ ] Given an empty message, the system returns a validation error — no crash.
- [ ] Given an unrecognised query type, the system returns a safe fallback answer.
- [ ] Given a malformed model response, the system catches it and returns a graceful error.
- [ ] Given a valid request, the response always includes `success`, `answer`, `request_id`.

---

## Evidence Level

| Claim | Evidence Level |
|---|---|
| Students need doubt clarification | Confirmed — core product purpose |
| Text-only input is sufficient for V1 | [ASSUMPTION] — image/audio deferred |
| Mock classifier is sufficient for V1 validation | [ASSUMPTION] — real classifier deferred to V2 |
| Non-streaming response is acceptable for V1 | Confirmed — streaming is a V2 non-goal |

---

## Risks / Open Questions

| Risk / Question | Label | Status |
|---|---|---|
| Real LLM not yet connected — V1 may use mock | [ASSUMPTION] | Open — SA to confirm |
| Classification categories not finalised | [NOT VERIFIED] | Open — BA to define V1 set |
| Model output structure not yet designed | [NOT VERIFIED] | Open — AI Architect to define |

---

## Dependencies

| Dependency | Status |
|---|---|
| Demo agent foundation (`app/main.py`, schemas, logging) | Available |
| LangGraph + Pydantic + AgentCore runtime | Available |
| Real LLM (Bedrock) | TODO — V1 uses mock if not ready |
| Real classifier model | TODO — V1 uses stub |

---

## Release Recommendation

**Proceed to BA phase.**

V1 scope is deliberately minimal to validate the core pipeline.
Non-goals are clearly bounded. No V1 dependency requires DynamoDB, KB, or streaming.
