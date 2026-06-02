---
name: meritranker-project-skills
description: Orchestrates MeritRanker Tutor repo-local skills and AI development roles from skills/. Reads AGENTS.md, core rules, feature context, and applies roles contextually for quality, bug-free code. Use when working in this repository, implementing features, fixing bugs, reviewing changes, or when the user wants project-standard quality.
---

# MeritRanker Project Skills & Roles

Apply **all relevant** repo guidance under `skills/` on every task. Run **roles contextually** — not every role on every change, but never skip required evidence or gates.

## Always read first

1. [AGENTS.md](../../../AGENTS.md) — repo boundaries, hard rules, role sequence
2. [skills-index.md](skills-index.md) — linked index of every `skills/` file
3. Matching [skills/features/<feature>.md](../../../skills/features/) for the feature in scope

## Default knowledge load (by task type)

| Task type | Core files (read before acting) | Feature file |
|---|---|---|
| Any code change | `coding-standards.md`, `architecture-principles.md`, `testing-and-debugging.md` | Yes |
| Graph / workflow | + `langgraph-patterns.md`, `pydantic-schemas.md` | Yes |
| Schema / API contract | + `pydantic-schemas.md`, `integration-boundaries.md` | Yes |
| Deploy / AgentCore | + `agentcore-runtime.md` | Yes |
| LLM / prompts / tools | + `langgraph-patterns.md`, `security-and-privacy.md`, `performance-and-scalability.md` | Yes |
| External integration | + `integration-boundaries.md`, `security-and-privacy.md` | Yes |
| Docs-only | `documentation-rules.md` | Yes |

Paths are under `skills/core/` unless noted.

## Contextual role workflow

Pick the **minimum role set** that satisfies the task. Escalate when scope, risk, or ambiguity grows.

### Role selection matrix

| User intent | Active roles (in order) | Planning required? |
|---|---|---|
| New feature / major capability | PM → BA → Solution Architect → AI Solution Architect → Engineer → (Architect re-check) → QA + Security + Performance + Docs → Release Gatekeeper | Yes — no code until 1–4 align |
| Prompt / generator / classifier wording changes | Prompt Engineer → Python Agent Engineer (if code) → QA | Plan or task brief for prompt scope |
| Approved implementation only | Python Agent Engineer → QA (+ Security/Performance if applicable) → Docs Maintainer | Plan must exist |
| Bug fix | Engineer (use bugfix template) → QA → Security if logs/auth/secrets touched | Light — document in bugfix report |
| Small fix (typo, comment, single-line) | Engineer hat + `make check` | No |
| Code / PR review | QA Reviewer; add Security + Performance for risky areas | No |
| Architecture question | Solution Architect (+ AI Solution Architect if graphs/LLM) | No |
| Release / merge readiness | All prior evidence → Release Gatekeeper | Evidence from reviews |
| Documentation sync | Documentation Maintainer | No |

### Role files (read the active role guide before acting)

| Role | Guide |
|---|---|
| Product Manager | [skills/roles/product-manager.md](../../../skills/roles/product-manager.md) |
| Business Analyst | [skills/roles/business-analyst.md](../../../skills/roles/business-analyst.md) |
| Solution Architect | [skills/roles/solution-architect.md](../../../skills/roles/solution-architect.md) |
| AI Solution Architect | [skills/roles/ai-solution-architect.md](../../../skills/roles/ai-solution-architect.md) |
| Python Agent Engineer | [skills/roles/python-agent-engineer.md](../../../skills/roles/python-agent-engineer.md) |
| Prompt Engineer | [skills/roles/prompt-engineer.md](../../../skills/roles/prompt-engineer.md) |
| QA Reviewer | [skills/roles/qa-reviewer.md](../../../skills/roles/qa-reviewer.md) |
| Security Reviewer | [skills/roles/security-reviewer.md](../../../skills/roles/security-reviewer.md) |
| Performance-Cost Reviewer | [skills/roles/performance-cost-reviewer.md](../../../skills/roles/performance-cost-reviewer.md) |
| Documentation Maintainer | [skills/roles/documentation-maintainer.md](../../../skills/roles/documentation-maintainer.md) |
| Release Gatekeeper | [skills/roles/release-gatekeeper.md](../../../skills/roles/release-gatekeeper.md) |

Role boundaries: [skills/roles/README.md](../../../skills/roles/README.md)

## Output templates (use when producing role deliverables)

Match template to role — see [skills/templates/README.md](../../../skills/templates/README.md). Do not delete template sections; use `N/A`, `[NOT VERIFIED]`, or `[BLOCKER]` as needed.

## Completion gates (every code change)

```
- [ ] Read AGENTS.md + relevant skills/core/*.md + skills/features/<feature>.md
- [ ] Acted in correct role(s); escalated if scope changed
- [ ] Code only in app/; no secrets; schemas unchanged unless approved
- [ ] Tests added/updated for behavior changes
- [ ] make check passes
- [ ] agentcore validate passes (if agentcore/ or deploy touched)
- [ ] skills/features/<feature>.md updated (if feature code changed)
- [ ] Unverified items labeled [NOT VERIFIED] — never claim certainty without evidence
```

## Hard rules (never violate)

From AGENTS.md — summarize only; full text is authoritative:

- No FastAPI; AgentCore provides HTTP
- No infra (DynamoDB, Redis, S3, KB) unless explicitly requested
- No real LLM calls in demo/foundation unless explicitly requested
- `agentcore/` = config only; all Python in `app/`
- Pydantic v2 at API boundaries; LangGraph for workflows
- Do not break public schemas without explicit approval + tests

## When to expand scope

Stop and run additional planning roles (PM → BA → Architects) if:

- Requirements are unclear or acceptance criteria missing
- Public schema or graph topology would change
- New external integration or infrastructure is needed
- Security, AI, or performance risk is unclear

## Additional resources

- Full linked index: [skills-index.md](skills-index.md)
- Skills directory overview: [skills/README.md](../../../skills/README.md)
