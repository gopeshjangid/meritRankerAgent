# Roadmap

This roadmap describes realistic direction for **MeritRanker Agent Python**. It is not a commitment to dates or funding. Items may be reprioritized as the project evolves.

**Current stage:** Early-stage, actively developed open-source toolkit. Core doubt-solving workflows exist with mock and real LLM paths; production hardening and broader feature coverage are ongoing.

---

## Phase 1 — Foundation (in progress)

**Goal:** A credible, testable Python agent runtime for education workflows.

| Area | Status |
|---|---|
| AgentCore + LangGraph runtime | Available |
| Pydantic v2 request/response schemas | Available |
| Mock-first local development (no credentials) | Available |
| pytest + ruff quality gate (`make check`) | Available |
| LLM orchestration (routes, registry, providers) | Available |
| Doubt solver graph (legacy + orchestrated paths) | Available |
| Answer quality validation and completion guards | Available |
| Streaming doubt solver service | Available |
| Provider adapters (Azure OpenAI, OpenAI, mock, others) | Partial — expanding |
| Documentation for contributors and operators | In progress |

---

## Phase 2 — Doubt solver maturity

**Goal:** Reliable student-facing doubt resolution for exam-prep subjects.

- Improve model routing benchmarks (math, reasoning, general)
- Tiered streaming vs. buffered validation by difficulty
- Stronger classifier and retrieval hint accuracy
- Optional Bedrock Knowledge Base and record retrieval integration
- Multilingual prompt and response support (EN / HI / Hinglish direction)
- Expanded integration and regression tests

---

## Phase 3 — Structured learning workflows

**Goal:** Move beyond single-turn Q&A toward guided learning.

- Structured reasoning steps in generator outputs
- Practice guidance flows (hints, follow-up questions, mistake patterns)
- Solution brief / planner scaffolding (initial modules exist)
- Educator review hooks (draft answers, review states — design TBD)
- Additional LangGraph workflows beyond doubt solver

---

## Phase 4 — Evaluation and educator tooling

**Goal:** Support validation, review, and improvement loops.

- Answer validation and evaluation utilities
- Benchmark harnesses for subject/difficulty routes
- Feedback capture for model and prompt iteration
- Export-friendly schemas for LMS or internal review tools

---

## Phase 5 — Production readiness (optional deployments)

**Goal:** Safer operation for teams deploying to AWS via AgentCore.

- Deployment runbooks and environment validation
- Observability patterns (structured logs, trace IDs — no secret leakage)
- Cost and latency profiling per route
- Hardened defaults for production (`APP_ENV=production` guards)

---

## Explicitly deferred

These are directionally interesting but not committed:

- Full LMS integration
- Automated grading at scale
- Persistent student memory without privacy review
- Infrastructure beyond what AgentCore deployment requires

---

## How to influence the roadmap

Open a GitHub issue with:

- The education workflow you are trying to support
- Expected inputs/outputs (schemas)
- Whether mock-only or real-provider testing is required

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
