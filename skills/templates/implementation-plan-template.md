# Implementation Plan: <feature name>

> Role: Solution Architect
> Template: `skills/templates/implementation-plan-template.md`
> Instruction: Fill every section before any code is written.
> This plan must be approved before the Python Agent Engineer begins implementation.
> Delete this instruction block before submitting.

---

## Goal

<!-- One sentence: what this plan delivers. -->

---

## Non-Goals

<!-- What this plan explicitly does NOT include. -->

- ...
- ...

---

## Current Context

<!-- Where is the codebase today with respect to this feature?
     Reference existing files and their current state. -->

| Component | Current state |
|---|---|
| Relevant graph | `app/graphs/<name>.py` — exists / does not exist |
| Relevant schema | `app/schemas/<name>.py` — exists / does not exist |
| Relevant service | `app/services/<name>.py` — exists / does not exist |
| Feature context doc | `skills/features/<name>.md` — exists / does not exist |

---

## Architecture Decision

<!-- What architectural approach is being used, and why?
     Justify any non-obvious choices. Flag alternatives considered. -->

**Decision:**
> ...

**Alternatives considered:**
> ...

**[REQUIRES ARCHITECT ALIGNMENT]** if any decision changes `agentcore.json`,
adds a new runtime, changes the public schema, or adds infrastructure.

---

## Files to Add / Change

| File | Action | Description |
|---|---|---|
| `app/graphs/<name>_graph.py` | New / Modify | |
| `app/schemas/<name>.py` | New / Modify | |
| `app/services/<name>_service.py` | New / Modify | |
| `app/tools/<name>_tool.py` | New / Modify / None | |
| `app/prompts/<name>.md` | New / Modify / None | |
| `app/tests/test_<name>.py` | New / Modify | |
| `skills/features/<name>.md` | Update | Feature context doc |

---

## Data Flow

<!-- Describe the flow from inbound request through graph to response.
     Use: INPUT → node_a → node_b → OUTPUT -->

```
AgentRequest (validated at main.py)
  → <start_node>: ...
  → <middle_node>: ...
  → <respond_node>: ...
AgentResponse
```

---

## Service Boundaries

<!-- List every external integration on the path, and confirm it goes through a service. -->

| Integration | Service file | Status |
|---|---|---|
| | `app/services/<name>.py` | Active / TODO / [NOT VERIFIED] |

---

## Schema / Contract Changes

<!-- List all additions or changes to public request/response schemas. -->

| Schema | Field | Change type | Backward-compatible? |
|---|---|---|---|
| `AgentRequest` | | None / Add / Modify / Remove | Yes / No |
| `AgentResponse` | | None / Add / Modify / Remove | Yes / No |

**[REQUIRES ARCHITECT ALIGNMENT]** Any breaking change must be discussed before proceeding.

---

## Config / Env Changes

| Variable | Purpose | Default | Required for deploy? |
|---|---|---|---|
| | | | Yes / No |

<!-- If none: write "No new env vars required." -->

---

## Testing Plan

| Scenario | File | Test name | Type |
|---|---|---|---|
| Happy path | `app/tests/test_<name>.py` | `test_...` | Unit |
| Validation failure | `app/tests/test_<name>.py` | `test_...` | Unit |
| Service failure | `app/tests/test_<name>.py` | `test_...` | Unit |
| Graph route condition | `app/tests/test_<name>.py` | `test_...` | Graph |

---

## Security Notes

| Concern | Assessment | Label |
|---|---|---|
| Input validation | Handled by Pydantic at entrypoint | |
| Auth | [AUTH TODO] — not implemented | [PROD BLOCKER] |
| Secrets | None hardcoded | |
| External output validation | Service returns Pydantic model | [AI RISK] if not |
| Logging | No PII or payloads at INFO level | |

---

## Performance / Cost Notes

| Concern | Assessment | Label |
|---|---|---|
| Model calls per request | | [PERFORMANCE RISK] if > 1 |
| Retrieval calls per request | | [PERFORMANCE RISK] if unbounded |
| External HTTP calls | | [PERFORMANCE RISK] if in loop |
| Prompt size | | [PERFORMANCE RISK] if unbounded |

---

## Risks

| Risk | Likelihood | Impact | Label | Mitigation |
|---|---|---|---|---|
| | Low/Med/High | Low/Med/High | | |

---

## Rollback / Disable Plan

<!-- How can this feature be disabled or rolled back if it fails in production? -->

> ...

---

## Acceptance Criteria

- [ ] All functional requirements from BA spec are implemented.
- [ ] `make check` passes (0 ruff errors, all tests green).
- [ ] `agentcore validate` passes.
- [ ] Feature context doc updated.
- [ ] No secrets hardcoded.
- [ ] Schema changes are backward-compatible, or breaking change is approved.

---

## Handoff to Engineer

**Approved by:** <!-- Solution Architect name or "Self-reviewed" -->
**Date:** <!-- YYYY-MM-DD -->

**Start with:** <!-- The first file or function to implement -->

**Known unknowns / [NOT VERIFIED] items the engineer should flag:**
- ...

**Out of bounds — do not implement:**
- ...
