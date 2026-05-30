# Release Gate: <feature / task name>

> Role: Release Gatekeeper
> Template: `skills/templates/release-gate-template.md`
> Instruction: Fill every section based on collected evidence from all review roles.
> The Release Gatekeeper does NOT review code directly.
> Every section must cite specific role outputs — do not assume or summarise vaguely.
> Delete this instruction block before submitting.

---

## Final Decision

<!-- Choose exactly one: APPROVE | APPROVE WITH RISKS | BLOCK -->

**BLOCK**

<!-- Replace with actual decision above. Reason in Final Reason section. -->

---

## Evidence Reviewed

| Artefact | Received? | Role | Notes |
|---|---|---|---|
| Product Brief | Yes / No / N/A | Product Manager | |
| BA Requirements | Yes / No / N/A | Business Analyst | |
| Implementation Plan | Yes / No / N/A | Solution Architect | |
| AI Architecture Plan | Yes / No / N/A | AI Solution Architect | |
| Implementation Report | Yes / No / N/A | Python Agent Engineer | |
| QA Review | Yes / No / N/A | QA Reviewer | |
| Security Review | Yes / No / N/A | Security Reviewer | |
| Performance-Cost Review | Yes / No / N/A | Performance-Cost Reviewer | |
| Documentation Update | Yes / No / N/A | Documentation Maintainer | |

---

## Role Outputs Received

| Role | Recommendation | Date |
|---|---|---|
| QA Reviewer | PASS / PASS WITH NOTES / FAIL / BLOCK | YYYY-MM-DD |
| Security Reviewer | PASS / PASS WITH WARNINGS / FAIL / BLOCK | YYYY-MM-DD |
| Performance-Cost Reviewer | PASS / PASS WITH NOTES / FAIL / BLOCK | YYYY-MM-DD |
| Documentation Maintainer | Complete / Incomplete | YYYY-MM-DD |

**[BLOCK]** if any role output is missing or has recommendation of FAIL or BLOCK.

---

## Blockers

<!-- List all unresolved BLOCKER or PROD BLOCKER items from any role. -->

| # | Blocker | Source role | Label | Resolution required |
|---|---|---|---|---|
| 1 | | | [BLOCKER] / [PROD BLOCKER] | |

<!-- If no blockers: write "None." -->

---

## Approved Risks

<!-- List any risks acknowledged and accepted by all relevant roles. -->

| # | Risk | Label | Accepted by | Condition |
|---|---|---|---|---|
| 1 | [AUTH TODO] — no user identity verification | [PROD BLOCKER] | All roles | Demo only — not for production |

---

## Deferred Items

<!-- List items that are intentionally deferred to a future task. -->

| # | Item | Label | Deferred until |
|---|---|---|---|
| 1 | | [DEFER] | |

<!-- If nothing deferred: write "None." -->

---

## Test / Lint / Runtime Status

| Check | Status | Source |
|---|---|---|
| `ruff check` | PASS / FAIL / [NOT VERIFIED] | Implementation Report |
| `pytest` (`N` tests) | PASS / FAIL / [NOT VERIFIED] | Implementation Report |
| `agentcore validate` | PASS / FAIL / [NOT VERIFIED] | Implementation Report |

---

## Documentation Status

| Check | Status | Source |
|---|---|---|
| Feature context doc updated | Yes / No / [NOT VERIFIED] | Documentation Update |
| AGENTS.md Skills Index updated | Yes / N/A / [NOT VERIFIED] | Documentation Update |
| Core docs updated where needed | Yes / N/A / [NOT VERIFIED] | Documentation Update |

---

## Security Status

| Check | Status | Source |
|---|---|---|
| Security Review recommendation | PASS / PASS WITH WARNINGS / FAIL / BLOCK | Security Reviewer |
| No hardcoded secrets | Confirmed / [NOT VERIFIED] | Security Reviewer |
| Auth gaps documented | Yes / [NOT VERIFIED] | Security Reviewer |
| PII handling documented | Yes / [NOT VERIFIED] | Security Reviewer |

---

## Performance-Cost Status

| Check | Status | Source |
|---|---|---|
| Performance-Cost recommendation | PASS / PASS WITH NOTES / FAIL / BLOCK | Perf-Cost Reviewer |
| Model call count per request | N (documented) / [NOT VERIFIED] | Perf-Cost Reviewer |
| External call timeouts set | Yes / No / [NOT VERIFIED] | Perf-Cost Reviewer |
| Prompt/context size bounded | Yes / No / [NOT VERIFIED] | Perf-Cost Reviewer |

---

## Final Reason

<!-- Write 2–4 sentences justifying the decision.
     Name specific role outputs and findings.
     Do not write "everything looks good" — cite evidence. -->

> ...

---

## Required Follow-up

<!-- Tasks that must be completed before or shortly after release. -->

| # | Task | Priority | Owner |
|---|---|---|---|
| 1 | | Must before release / Must after release / [DEFER] | |

<!-- If no follow-up required: write "None." -->
