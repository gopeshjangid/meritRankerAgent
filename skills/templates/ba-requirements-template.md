# BA Requirements: <feature name>

> Role: Business Analyst
> Template: `skills/templates/ba-requirements-template.md`
> Instruction: Fill every section. Use [NOT VERIFIED] if a fact is not confirmed.
> Do not design implementation. Describe behaviour and rules only.
> Delete this instruction block before submitting.

---

## Requirement Summary

<!-- One paragraph: what this feature does, who it serves, and what the success outcome is. -->

---

## Actors / Users

| Actor | Role | Interaction |
|---|---|---|
| Student | Primary user | ... |
| System | Automated | ... |

---

## Functional Requirements

<!-- Number each requirement. Write in: "The system SHALL..." or "The system MUST..." -->

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| FR-01 | The system SHALL ... | Must | |
| FR-02 | The system SHALL ... | Should | |
| FR-03 | The system SHALL ... | Nice to have | |

**Priority key:** Must (MVP) | Should (strong value) | Nice to have (deferred)

---

## Input / Output Specification

### Input

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `message` | `str` | Yes | min 1, max 5000 chars | User's question or request |
| `user_id` | `str` | Yes | min 1, max 128 chars | Identifies the student |
| `mode` | `str` | Yes | enum: see config | Feature routing mode |

### Output

| Field | Type | Always present | Notes |
|---|---|---|---|
| `success` | `bool` | Yes | |
| `answer` | `str \| null` | On success | |
| `request_id` | `str` | Yes | |
| `error` | `str \| null` | On failure | |

---

## User Scenarios

<!-- Describe the main expected usage paths. Plain language. No code. -->

**Scenario 1: Happy path**
> User sends ... System returns ...

**Scenario 2: Edge case — empty input**
> User sends ... System returns ...

**Scenario 3: Failure case**
> System cannot ... User receives ...

---

## Edge Cases

<!-- List all boundary conditions, invalid inputs, and unusual but valid states. -->

| Edge Case | Expected Behaviour |
|---|---|
| Empty message | Validation error returned |
| Message at max length | Accepted and processed normally |
| Unknown mode value | Validation error returned |
| Service unavailable | Graceful error response, no exception to caller |

---

## Acceptance Criteria

<!-- One-to-one mapping with Functional Requirements where possible.
     Each criterion must be independently testable. -->

| ID | Criterion | Linked FR |
|---|---|---|
| AC-01 | Given ... when ... then ... | FR-01 |
| AC-02 | Given ... when ... then ... | FR-02 |

---

## Requirement-to-Test Mapping

<!-- Maps each requirement to one or more planned test cases. -->

| Requirement | Test File | Test Name | Status |
|---|---|---|---|
| FR-01 | `app/tests/test_<feature>.py` | `test_...` | Planned / Exists |
| FR-02 | `app/tests/test_<feature>.py` | `test_...` | [NOT VERIFIED] |

---

## Non-Goals

<!-- What is explicitly out of scope for this requirements set? -->

- ...
- ...

---

## Data Sensitivity Notes

<!-- Does this feature handle PII, student data, or sensitive information? -->

| Data Field | Sensitivity | Handling Required |
|---|---|---|
| `message` | Potentially PII | Do not log full content at INFO level |
| `user_id` | Student identifier | Do not expose in error messages |

<!-- If no sensitive data: write "None identified at this stage." -->

---

## Dependency Failure Expectations

<!-- What should happen if a downstream service fails? -->

| Service | Failure Mode | Expected System Behaviour |
|---|---|---|
| Mock LLM service | Returns empty string | Return `success=False` with user-visible error |
| DynamoDB (TODO) | Timeout | [NOT VERIFIED — not yet implemented] |

---

## Open Questions

<!-- Questions that remain unresolved and block or risk the requirements. -->

| # | Question | Owner | Status |
|---|---|---|---|
| 1 | | | Open |

---

## Assumptions

<!-- List all assumptions made in this document. -->

| # | Assumption | Label |
|---|---|---|
| 1 | | [ASSUMPTION] |

---

## Blockers

<!-- Any issue that prevents these requirements from being safely implemented. -->

| # | Blocker | Label | Resolution Path |
|---|---|---|---|
| 1 | | [BLOCKER] / [PROD BLOCKER] | |

<!-- If no blockers: write "None." -->
