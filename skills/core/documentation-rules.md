# Documentation Rules — meritRankerTutor

> Rules for keeping `skills/` docs in sync with the code.
> These rules apply to **every coding agent on every task.**

---

## The Core Rule

> **If docs and code disagree, the task is not complete.**

Updating code without updating the matching feature context file is an
incomplete task, even if tests pass.

---

## Feature Context Files

Every feature has exactly one file: `skills/features/<feature-name>.md`.

### When to create a new file

When you add:
- A new graph (e.g., `question_solver_graph.py`)
- A new primary workflow or user-facing capability
- A new set of schemas for a distinct feature

Create: `skills/features/question-solver.md`

### When to update an existing file

When you:
- Add or change a node in the graph
- Add a new service or change a service interface
- Add a new schema field to a request/response model
- Add, remove, or change a tool
- Change the entrypoint behaviour
- Fix a bug that changes documented behaviour
- Add tests

Update the relevant `skills/features/<name>.md` in the **same task**.

---

## Feature Context File Requirements

Every `skills/features/<name>.md` must contain:

| Section | Mandatory? | Contents |
|---|---|---|
| `## Purpose` | Yes | What this feature does, for whom |
| `## Current Status` | Yes | `demo` / `in-progress` / `production` |
| `## Entrypoints` | Yes | Which `main.py` entrypoint(s) serve this feature |
| `## Graphs` | Yes | Graph file(s) and high-level node description |
| `## Schemas` | Yes | Request, response, and state schema files |
| `## Services` | Yes | Services used, with brief description |
| `## Tools` | Yes | Tools used, or "None" if empty |
| `## Prompts` | Yes | Prompt files, or "None" if unused |
| `## Tests` | Yes | Test files covering this feature |
| `## Config / Env` | Yes | Env vars specific to this feature |
| `## Known Limitations` | Yes | Honest list of missing capabilities |
| `## Latest Changes` | Yes | Reverse-chronological list of changes |
| `## Next Steps` | Recommended | Planned improvements |

---

## Architectural Decision Records

When a significant architectural decision is made:

1. Add a dated entry to `skills/core/architecture-principles.md` under
   "Decision Record".
2. Format: `YYYY-MM-DD — <decision title> — <brief rationale>`

---

## Core Skill File Updates

Update `skills/core/*.md` when:

- A new project-wide coding convention is established.
- A new pattern is identified as the preferred approach.
- A previously recommended approach is deprecated.

---

## What Not to Do

- Do not leave `## Latest Changes` blank after making a change.
- Do not copy-paste large code blocks into docs — reference file paths instead.
- Do not describe future intent as current fact ("the system uses X" when X is TODO).
- Do not let a feature file become out of date for more than one task cycle.
- Do not claim something is verified when it was not tested. Use `[NOT VERIFIED]` explicitly.
- Do not omit blockers from docs. If something prevents safe implementation, mark it `[BLOCKER]` or `[PROD BLOCKER]` in the feature context.

---

## Label Usage in Docs

Use standard labels so any agent can scan docs for risks:

| Label | When to use in docs |
|---|---|
| `[ASSUMPTION]` | Decision based on expected behaviour, not confirmed |
| `[NOT VERIFIED]` | Capability assumed but not confirmed in this runtime/environment |
| `[BLOCKER]` | Unresolved issue that blocks implementation |
| `[PROD BLOCKER]` | Must be resolved before production deployment |
| `[AI RISK]` | Risk from model, retrieval, prompt, or tool-use behaviour |
| `[SECURITY RISK]` | Potential security vulnerability or exposure |
| `[PERFORMANCE RISK]` | Likely latency or cost problem at scale |
| `[AUTH TODO]` | Auth not yet implemented — documented here explicitly |
| `[DEFER]` | Real concern, not needed at current scale — revisit later |

**Rule:** Never use vague language as a substitute for a label.
"We'll add auth later" → `[AUTH TODO]`
"This might be slow" → `[PERFORMANCE RISK]`
"We assume this works" → `[ASSUMPTION]` or `[NOT VERIFIED]`

---

## Enforcement

A coding agent must self-check before completing any task:

```
□ Did I change any Python file in app/?
□ If yes — which feature does it belong to?
□ Is skills/features/<feature-name>.md updated to reflect my changes?
□ If I made an architectural decision — is it in architecture-principles.md?
□ Did I use [NOT VERIFIED] for anything I could not confirm?
□ Did I mark unresolved blockers as [BLOCKER] or [PROD BLOCKER]?
□ Does make check still pass?
```

If any box is unchecked, the task is not done.
