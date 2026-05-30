# Documentation Update: <feature / task name>

> Role: Documentation Maintainer
> Template: `skills/templates/documentation-update-template.md`
> Instruction: Complete this after every feature change or bug fix.
> Check every section — do not leave mandatory sections blank.
> Refer to `skills/core/documentation-rules.md` for project documentation rules.
> Delete this instruction block before submitting.

---

## Updated Feature Context

<!-- List every `skills/features/<name>.md` file touched, and what changed. -->

| File | Updated? | What changed |
|---|---|---|
| `skills/features/<name>.md` | Yes / No / [DOCS TODO] | |

**[BLOCKER]** If the feature context doc was not updated, this task is not complete.

---

## Updated Feature Index

<!-- Was `skills/features/<name>.md` added to the Skills Index in AGENTS.md? -->

| Check | Status |
|---|---|
| New feature doc listed in AGENTS.md Skills Index | Yes / N/A (existing feature) / [DOCS TODO] |

---

## Updated Core Docs

<!-- Were any core engineering rules affected by this change? -->

| File | Updated? | Reason |
|---|---|---|
| `skills/core/architecture-principles.md` | Yes / No | <!-- If a new architectural decision was made --> |
| `skills/core/integration-boundaries.md` | Yes / No | <!-- If a new service was added --> |
| `skills/core/security-and-privacy.md` | Yes / No | <!-- If a new security pattern was used --> |
| `skills/core/performance-and-scalability.md` | Yes / No | <!-- If a performance profile changed --> |
| Other | Yes / No | |

---

## Updated AGENTS.md

<!-- Was AGENTS.md affected? -->

| Change | Made? | Notes |
|---|---|---|
| New feature in Skills Index | Yes / No / N/A | |
| New role or workflow rule | Yes / No / N/A | |
| Pre-flight checklist update | Yes / No / N/A | |

---

## Documentation Change Summary

<!-- One paragraph: describe what was added, changed, or removed across all docs. -->

> ...

---

## Verification Summary

<!-- What evidence confirms docs are accurate and not stale? -->

| Check | Status |
|---|---|
| Feature context reflects current code | Yes / [NOT VERIFIED] |
| No "TODO" sections left blank | Yes / No — see Not Verified below |
| No future intent described as current fact | Yes / No |
| `## Latest Changes` entry added with today's date | Yes / No |

---

## Not Verified

<!-- Any documentation claim that could not be confirmed against the codebase. -->

| Claim | Doc location | Label |
|---|---|---|
| | `skills/features/...` | [NOT VERIFIED] |

<!-- If all claims verified: write "None." -->

---

## Follow-up Needed

<!-- Documentation gaps that need to be resolved in a future task. -->

- [ ] ...

<!-- If nothing outstanding: write "None." -->
