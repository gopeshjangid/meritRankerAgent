# Project Overview — MeritRanker Tutor

> This file is context, not an implementation plan.
> Read it to understand what this project is and where it is heading.

---

## What This Project Is

**MeritRanker Tutor** is a Python AgentCore + LangGraph runtime for tutoring and
student-facing agent workflows.

The system receives student or educator requests via the AgentCore HTTP layer,
processes them through controlled LangGraph workflows, and returns structured responses.
The architecture is designed to be incrementally replaced — mock services first,
real integrations later — without changing the graph or entrypoint contracts.

---

## Current Base (Foundation Stage)

| Component | Current State |
|---|---|
| AgentCore runtime | Local dev + deployment config in `agentcore/` |
| Python application root | `app/` — single runtime, single entrypoint |
| LangGraph graph | `demo_graph.py` — two-node demo workflow |
| Schemas | `AgentRequest`, `AgentResponse`, `AgentState` (Pydantic v2) |
| Services | `mock_response_service.py` — canned response, no real LLM |
| Tests | 17 pytest tests — schemas + graph, no network required |
| Logging | Rich-formatted, includes `request_id` |
| CI gate | `make check` — ruff + pytest |

---

## Planned Growth

Features will be added in phases. This list describes direction, not schedule.

### Phase 2 — Question Solver

- Add `question_solver_graph.py` in `app/graphs/`.
- Add `QuestionRequest` / `QuestionResponse` schemas.
- Add `bedrock_llm_service.py` to replace mock service.
- Route based on `mode` field in `AgentRequest`.
- Add `skills/features/question-solver.md`.

### Phase 3 — DynamoDB Question Fetch

- Add `dynamodb_question_service.py` in `app/services/`.
- Fetch question data by `question_id` from DynamoDB.
- Graph node calls service — never accesses DynamoDB directly.
- IAM access controlled via `agentcore/agentcore.json` credentials block.

### Phase 4 — Bedrock Knowledge Base Retrieval

- Add `bedrock_kb_service.py` in `app/services/`.
- Retrieve context passages for RAG-style answering.
- Injected as context into prompt template.
- Retrieved content treated as untrusted until validated. [AI RISK]

### Phase 5 — Model Routing

- Add `model_router_service.py` or equivalent.
- Route to different models by `mode`, question type, or cost target.
- Provider-specific logic hidden behind service boundary.

### Phase 6 — Study Planner

- Add `study_plan_graph.py`.
- Accepts student profile + goals.
- Returns structured study plan via Pydantic response schema.

### Phase 7 — Memory and Cache

- Session memory via AgentCore memory resource or DynamoDB.
- Semantic cache for repeated queries — added only when justified by load.
- All cache/memory access behind service boundaries.

---

## Constraints That Do Not Change

These constraints apply regardless of which phase the project is in:

- No FastAPI. AgentCore owns the HTTP layer.
- No secrets hardcoded. Env vars only.
- No direct cloud/provider calls inside graph nodes.
- All external integrations behind `app/services/`.
- Pydantic validates inbound requests and outbound responses.
- Tests must run without AWS credentials unless explicitly approved.
- `make check` must pass at all times.

---

## [ASSUMPTION] Items

- `[ASSUMPTION]` Bedrock Knowledge Base will be used for RAG — may change to another retrieval system.
- `[ASSUMPTION]` DynamoDB will be used for question storage — schema not yet designed.
- `[ASSUMPTION]` AgentCore memory resource will handle session context — not yet confirmed for this use case. [NOT VERIFIED]
