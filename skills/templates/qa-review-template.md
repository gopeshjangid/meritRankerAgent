# QA Review: <feature / task name>

> Role: QA Reviewer
> Template: `skills/templates/qa-review-template.md`
> Instruction: Fill every section based on evidence only — no assumptions as facts.
> If evidence is missing, write [NOT VERIFIED] with an explanation.
> Delete this instruction block before submitting.

---

## Recommendation

<!-- Choose exactly one: PASS | PASS WITH NOTES | FAIL | BLOCK -->

**PASS WITH NOTES**

<!-- Replace with actual recommendation above. Reason in Final Decision Reason section. -->

---

## Evidence Checked

<!-- List every artefact reviewed. Do not claim to have checked something you have not. -->

| Artefact | Checked? | Notes |
|---|---|---|
| BA requirements doc | Yes / No / [NOT VERIFIED] | |
| Implementation report | Yes / No / [NOT VERIFIED] | |
| Changed files | Yes / No / [NOT VERIFIED] | |
| Test suite output (`pytest`) | Yes / No / [NOT VERIFIED] | |
| Lint output (`ruff check`) | Yes / No / [NOT VERIFIED] | |
| `agentcore validate` output | Yes / No / [NOT VERIFIED] | |
| Feature context doc | Yes / No / [NOT VERIFIED] | |

---

## Requirements Coverage

<!-- Map each BA acceptance criterion to a test. -->

| BA Criterion | Test file | Test name | Status |
|---|---|---|---|
| AC-01: ... | `app/tests/test_<name>.py` | `test_...` | Covered / Missing / [NOT VERIFIED] |
| AC-02: ... | | | Missing |

---

## Checklist Result

| Check | Result | Notes |
|---|---|---|
| All AC from BA spec covered by tests | Pass / Fail | |
| Happy path tested | Pass / Fail | |
| Validation failure paths tested | Pass / Fail | |
| Service failure paths tested | Pass / Fail | |
| No test imports `boto3`, `requests`, or real infra | Pass / Fail | |
| Tests run without AWS credentials | Pass / Fail | |
| No test relies on external network | Pass / Fail | |
| `pytest` output shows all green | Pass / Fail | |
| `ruff check` shows 0 errors | Pass / Fail | |

---

## Missing Tests

<!-- List any scenarios that are not covered by existing tests. -->

| Scenario | Risk if untested | Label |
|---|---|---|
| | Low / Medium / High | |

<!-- If all scenarios covered: write "None identified." -->

---

## Regression Risks

<!-- What existing behaviour could this change break? -->

| Component | Risk | Mitigated? |
|---|---|---|
| `AgentRequest` schema | | Yes / No |
| `AgentResponse` schema | | Yes / No |
| Existing graph | | Yes / No |

---

## Blocking Findings

<!-- Issues that must be resolved before this can PASS.
     Use [BLOCKER] or [PROD BLOCKER]. -->

| # | Finding | Label | Resolution required |
|---|---|---|---|
| | | [BLOCKER] | |

<!-- If none: write "None." -->

---

## Non-Blocking Notes

<!-- Observations that do not block release but should be tracked. -->

- ...

---

## Documentation Status

| Doc | Status |
|---|---|
| `skills/features/<name>.md` | Up to date / Stale / [NOT VERIFIED] |

---

## Final Decision Reason

<!-- Write 1–3 sentences justifying the recommendation.
     Cite specific evidence — do not summarise with "everything looks good." -->

> ...
