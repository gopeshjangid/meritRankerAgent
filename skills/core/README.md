# skills/core/ — Project-Wide Engineering Rules

This directory contains **permanent, project-wide engineering rules** for the
MeritRanker Tutor AgentCore project.

Every AI coding agent (Claude Code, Codex, GitHub Copilot, Antigravity, etc.)
working on this repo must read the relevant core files before implementing anything.

---

## What Is in Each Directory

| Directory | Purpose |
|---|---|
| `skills/core/` | Permanent engineering rules — how the repo must be built |
| `skills/roles/` | Role behaviour guides — who is acting and what they own |
| `skills/features/` | Current feature state — what exists, what works, what is missing |
| `skills/templates/` | Reusable output formats for plans, reviews, bug reports, feature docs |

---

## Reading Order for Coding Agents

Before starting any task:

1. **`AGENTS.md`** — primary instruction file, repo boundaries, hard rules.
2. **Role file** — `skills/roles/<your-role>.md` — what your role owns and must not do.
3. **Core rules** — the relevant `skills/core/*.md` files for the task type.
4. **Feature context** — `skills/features/<feature>.md` — current state of the feature being changed.

---

## Core Files Index

| File | Covers |
|---|---|
| `project-overview.md` | What MeritRanker Tutor is and where it is going |
| `architecture-principles.md` | Layer boundaries, design rules, decision records |
| `agentcore-runtime.md` | AgentCore CLI, deployment model, local dev workflow |
| `coding-standards.md` | Python rules, ruff config, module layout, anti-patterns |
| `langgraph-patterns.md` | Graph file conventions, node rules, testing graphs |
| `pydantic-schemas.md` | Schema design, validation rules, stability rules |
| `integration-boundaries.md` | DynamoDB, Bedrock, model, cache, external call rules |
| `testing-and-debugging.md` | Test strategy, CI gate, mocking, debugging steps |
| `security-and-privacy.md` | Secrets, logging, auth, PII, prompt-injection rules |
| `performance-and-scalability.md` | Latency, model call count, cost, scaling rules |
| `documentation-rules.md` | Feature doc requirements, sync rules, labels |

---

## Labels Used Across Core Files

| Label | Meaning |
|---|---|
| `[ASSUMPTION]` | Decision based on expected behaviour, not confirmed fact |
| `[NOT VERIFIED]` | Capability assumed but not confirmed in this runtime |
| `[BLOCKER]` | Unresolved issue that blocks safe implementation |
| `[PROD BLOCKER]` | Must be resolved before production deployment |
| `[AI RISK]` | Risk from model, retrieval, prompt, or tool-use behaviour |
| `[SECURITY RISK]` | Security vulnerability or exposure |
| `[PERFORMANCE RISK]` | Likely latency or cost problem at scale |
| `[AUTH TODO]` | Auth not yet implemented; document, do not hide |
