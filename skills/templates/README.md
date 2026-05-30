# Skills Templates — MeritRanker Tutor

> `skills/templates/` contains required output formats for all AI coding agent roles.
> Use the matching template when producing any plan, review, report, or release decision.

---

## Why Templates Exist

- **Reduce hallucination.** Structured sections force agents to look for evidence, not invent it.
- **Reduce inconsistency.** Every plan, review, and report from any role looks the same.
- **Make assumptions explicit.** Every template has a section for `[ASSUMPTION]` and `[NOT VERIFIED]` items.
- **Make blockers visible.** `[BLOCKER]` and `[PROD BLOCKER]` items can be scanned at a glance.

---

## Template Index

| Template | Used by | When |
|---|---|---|
| `product-brief-template.md` | Product Manager | Starting a feature |
| `ba-requirements-template.md` | Business Analyst | Requirements phase |
| `implementation-plan-template.md` | Solution Architect | Architecture/design phase |
| `ai-architecture-plan-template.md` | AI Solution Architect | AI workflow design phase |
| `feature-context-template.md` | All roles | Creating a `skills/features/<name>.md` file |
| `engineer-implementation-report-template.md` | Python Agent Engineer | After implementation |
| `qa-review-template.md` | QA Reviewer | QA phase |
| `security-review-template.md` | Security Reviewer | Security review phase |
| `performance-cost-review-template.md` | Performance-Cost Reviewer | Performance/cost review phase |
| `documentation-update-template.md` | Documentation Maintainer | After any feature change |
| `bugfix-report-template.md` | Python Agent Engineer | Bug fix tasks |
| `release-gate-template.md` | Release Gatekeeper | Release decision |

---

## How to Use

1. Copy the relevant template.
2. Fill in every section — do not delete sections.
3. If a section does not apply, write `N/A` or `None`.
4. If evidence is missing, write `[NOT VERIFIED]` with a brief explanation.
5. If a blocker exists, write `[BLOCKER]` or `[PROD BLOCKER]` with the detail.

**Rule:** Leaving a mandatory section blank is not acceptable. Use `[NOT VERIFIED]`
or `[DOCS TODO]` if the information is genuinely unknown — do not leave it empty.

---

## Standard Labels

| Label | Meaning |
|---|---|
| `[ASSUMPTION]` | A decision based on expected behaviour, not confirmed fact |
| `[NOT VERIFIED]` | Capability or fact assumed but not confirmed |
| `[BLOCKER]` | Unresolved issue that blocks implementation |
| `[PROD BLOCKER]` | Must be resolved before production deployment |
| `[AI RISK]` | Risk from model, retrieval, prompt, or tool-use behaviour |
| `[SECURITY RISK]` | Potential security vulnerability or exposure |
| `[PERFORMANCE RISK]` | Likely latency or cost problem at scale |
| `[REQUIRES ARCHITECT ALIGNMENT]` | A decision that needs architecture sign-off before proceeding |
| `[AUTH TODO]` | Auth not yet implemented — documented here explicitly |
| `[DEFER]` | Real concern, not needed at current scale — revisit later |

---

## Feature Context Files

Every feature must have a `skills/features/<feature-name>.md` file.
Use `feature-context-template.md` as the starting point.
This file must be updated whenever the feature's code changes.
If docs and code disagree, the task is not complete.
