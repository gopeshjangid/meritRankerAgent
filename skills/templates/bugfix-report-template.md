# Bugfix Report: <bug title>

> Role: Python Agent Engineer
> Template: `skills/templates/bugfix-report-template.md`
> Instruction: Fill every section. A regression test is mandatory for every bug fix.
> Do not mark the fix complete until `make check` passes and this report is filled.
> Delete this instruction block before submitting.

---

## Symptom

<!-- What does the user or system observe that is wrong?
     Be specific: what input, what output, what was expected. -->

**Observed:** <!-- What the system does wrong -->
**Expected:** <!-- What the system should do -->
**Severity:** Critical / High / Medium / Low
**First seen:** <!-- YYYY-MM-DD or "unknown" -->

---

## Root Cause

<!-- Where is the bug? Which file, function, line? Why does it happen? -->

**File:** `app/...`
**Function / line:** `...`

**Root cause explanation:**
> <!-- One paragraph. Be specific. Do not guess — write [NOT VERIFIED] if uncertain. -->

---

## Fix

<!-- What change resolves the bug? Keep it minimal and focused. -->

| File | Change |
|---|---|
| `app/...` | <!-- One-line description --> |

**Why this fix is correct:**
> <!-- Explain why the change resolves the root cause, not just the symptom. -->

---

## Tests Added / Updated

<!-- A regression test is mandatory. It must fail before the fix and pass after. -->

| Test file | Test name | Type | Fails before fix? |
|---|---|---|---|
| `app/tests/test_<name>.py` | `test_<bug>_regression` | Regression | Yes / [NOT VERIFIED] |

---

## Files Changed

| File | Action | Description |
|---|---|---|
| `app/...` | Modified | Fix |
| `app/tests/test_<name>.py` | Modified | Regression test added |
| `skills/features/<name>.md` | Updated | Known limitations / latest changes |

---

## Risk / Impact

<!-- What could this fix break? What was the blast radius of the original bug? -->

| Concern | Assessment | Label |
|---|---|---|
| Schema change | None / Breaking / Additive | |
| Other features affected | None / <!-- list --> | |
| Data integrity risk | None / <!-- describe --> | |

---

## Verification

| Check | Result |
|---|---|
| `ruff check` passes | Pass / Fail |
| `pytest` passes | Pass `N tests` / Fail |
| `agentcore validate` passes | Pass / Fail |
| Regression test fails before fix (confirmed) | Yes / [NOT VERIFIED] |
| Regression test passes after fix | Yes / Fail |
| No unrelated behaviour changed | Yes / [NOT VERIFIED] |

---

## Not Verified

<!-- Anything that could not be confirmed during this fix. -->

| Item | Label | Notes |
|---|---|---|
| | [NOT VERIFIED] | |

<!-- If all verified: write "None." -->

---

## Follow-up Needed

<!-- Related issues or tasks discovered during investigation. -->

- [ ] ...

<!-- If nothing outstanding: write "None." -->
