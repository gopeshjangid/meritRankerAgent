# Implementation Report: <task name>

> Role: Python Agent Engineer
> Template: `skills/templates/engineer-implementation-report-template.md`
> Instruction: Complete this report after implementation is done.
> Do not mark the task complete until `make check` passes and this report is filled.
> Delete this instruction block before submitting.

---

## Changed Files

| File | Action | Description |
|---|---|---|
| `app/...` | New / Modified / Deleted | <!-- One-line summary of change --> |
| `skills/features/<name>.md` | Updated | Feature context doc updated |

---

## Behaviour Implemented

<!-- Describe what the system now does that it did not before.
     One bullet per behaviour change. Reference the BA AC IDs if available. -->

- [ ] AC-01: ...
- [ ] AC-02: ...

---

## Impact Analysis

<!-- What other parts of the system could this change affect?
     List files, tests, schemas, or features that were NOT changed
     but depend on what was changed. -->

| Component | Impact |
|---|---|
| `app/schemas/...` | No change / Schema field added / Breaking change |
| `app/graphs/...` | No change / Node added |
| `app/tests/...` | No change / Tests updated |
| Other features | None / <!-- describe --> |

---

## Tests Added / Updated

| Test file | Test name | Covers |
|---|---|---|
| `app/tests/test_<name>.py` | `test_...` | <!-- What behaviour it verifies --> |

---

## Commands Run

<!-- List the commands run to verify the implementation. -->

```
cd app && uv run ruff check .
cd app && uv run pytest
agentcore validate
```

---

## Test / Lint Result

| Check | Result |
|---|---|
| `ruff check` | PASS / FAIL — <!-- error summary if failed --> |
| `pytest` | PASS `N tests` / FAIL — <!-- failure summary --> |
| `agentcore validate` | PASS / FAIL |

---

## Implementation Notes

<!-- Anything the reviewer needs to know about the approach taken.
     Include any deviation from the approved plan and the reason. -->

---

## Known Limitations

<!-- What does this implementation NOT handle?
     Use [NOT VERIFIED], [AUTH TODO], [DEFER], [PROD BLOCKER] labels. -->

- [AUTH TODO] No auth implemented — user identity not verified.
- [NOT VERIFIED] <!-- Any behaviour assumed but not confirmed. -->

---

## Documentation Status

| Doc file | Status |
|---|---|
| `skills/features/<name>.md` | Updated / Not updated — [DOCS TODO] |
| `skills/core/<relevant>.md` | Updated if architectural decision made / N/A |

---

## Unverified Items

<!-- List anything you could not confirm during implementation.
     Must use [NOT VERIFIED] label. -->

| Item | Label | Notes |
|---|---|---|
| | [NOT VERIFIED] | |

---

## Follow-up Needed

<!-- List tasks that are blocked on this implementation or should follow it. -->

- [ ] ...
