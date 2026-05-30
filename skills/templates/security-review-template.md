# Security Review: <feature / task name>

> Role: Security Reviewer
> Template: `skills/templates/security-review-template.md`
> Instruction: Fill every section based on evidence only.
> Use [NOT VERIFIED] where evidence is missing — never assume PASS without checking.
> Refer to `skills/core/security-and-privacy.md` for project security rules.
> Delete this instruction block before submitting.

---

## Recommendation

<!-- Choose exactly one: PASS | PASS WITH WARNINGS | FAIL | BLOCK -->

**PASS WITH WARNINGS**

<!-- Replace with actual recommendation above. Reason in Final Decision Reason section. -->

---

## Evidence Reviewed

| Artefact | Reviewed? | Notes |
|---|---|---|
| Changed Python files | Yes / No / [NOT VERIFIED] | |
| Pydantic schema definitions | Yes / No / [NOT VERIFIED] | |
| Service files | Yes / No / [NOT VERIFIED] | |
| Prompt templates | Yes / No / [NOT VERIFIED] | |
| Logging calls | Yes / No / [NOT VERIFIED] | |
| `app/.env.local` (no secrets in source?) | Yes / No / [NOT VERIFIED] | |
| `agentcore.json` credentials block | Yes / No / [NOT VERIFIED] | |
| `uv.lock` / dependency scan | Yes / No / [NOT VERIFIED] | |

---

## Findings

<!-- List every finding, blocking or not. Use the appropriate label. -->

| # | Finding | File / location | Label | Severity |
|---|---|---|---|---|
| 1 | | | [SECURITY RISK] / [AI RISK] / [PROD BLOCKER] | Critical / High / Medium / Low |

<!-- If no findings: write "None identified." -->

---

## Blocking Findings

<!-- Issues that must be resolved before this can PASS. -->

| # | Finding | Label | Resolution required |
|---|---|---|---|
| | | [BLOCKER] / [PROD BLOCKER] | |

<!-- If none: write "None." -->

---

## Production Auth Notes

<!-- Auth status at this release. Must be documented explicitly — never left blank. -->

| Auth concern | Status | Label |
|---|---|---|
| Inbound request identity verification | Not implemented — demo only | [AUTH TODO] |
| User-supplied `user_id` trusted? | Yes (demo only — not for production) | [PROD BLOCKER] |
| Session/token validation | Not implemented | [AUTH TODO] |

---

## Privacy Notes

<!-- Does this feature handle student data, PII, or sensitive content? -->

| Data field | Sensitivity | Logging status | Persistence status |
|---|---|---|---|
| `message` | Potentially PII | Not logged at INFO | Not persisted — [NOT VERIFIED] |
| `user_id` | Student identifier | Not exposed in errors | Not persisted — [NOT VERIFIED] |

---

## Dependency / Security Scan Status

| Check | Status | Notes |
|---|---|---|
| No secrets in `uv.lock` or `pyproject.toml` | Pass / [NOT VERIFIED] | |
| No known CVEs in direct dependencies | [NOT VERIFIED] — no automated scan configured | |
| No eval/exec/subprocess with user input | Pass / Fail | |
| No pickle deserialisation of untrusted data | Pass / [NOT VERIFIED] | |

---

## Final Decision Reason

<!-- Write 1–3 sentences justifying the recommendation.
     Cite specific evidence. Do not claim PASS without named evidence. -->

> ...
