# Review Checklist Template

> Use this template to structure a code or documentation review.
> Copy, fill in, and attach to the PR / task output.

---

## Review Summary

**Task / PR:** <!-- Link or description -->
**Reviewer:** <!-- Agent role or name -->
**Date:** <!-- YYYY-MM-DD -->
**Verdict:** <!-- Pass | Pass with notes | Fail -->

---

## Correctness

- [ ] Implementation matches the task description
- [ ] Edge cases handled (empty input, max-length values, invalid types)
- [ ] Error paths return sensible responses (not unhandled exceptions)
- [ ] No unintended side effects on unrelated features

---

## Testing

- [ ] `make check` passes (ruff + pytest)
- [ ] All new behaviour has at least one test
- [ ] Tests do not require network access or AWS credentials
- [ ] No test silently catches exceptions

---

## Code Quality

- [ ] No raw `dict` at module boundaries (Pydantic schemas used)
- [ ] No `print()` — `logger.*` used throughout
- [ ] No f-strings in log calls
- [ ] All function signatures are type-annotated
- [ ] Line length ≤ 100 characters
- [ ] No dead code or commented-out blocks

---

## Architecture

- [ ] Code is inside `app/`
- [ ] Graph nodes do not import `boto3`, `requests`, or external SDKs
- [ ] New external I/O goes through a service in `app/services/`
- [ ] No FastAPI, no Redis, no DynamoDB unless explicitly required

---

## Security

- [ ] No hardcoded secrets, keys, or tokens
- [ ] User input is validated by Pydantic before entering graph logic
- [ ] Logs do not contain PII or full user payloads
- [ ] No `eval()`, `exec()`, or `subprocess` with user-controlled input

---

## Documentation

- [ ] `skills/features/<name>.md` updated to match changes
- [ ] `## Latest Changes` section has a new dated entry
- [ ] `## Known Limitations` is accurate
- [ ] No doc section claims functionality that is not implemented

---

## Issues Found

<!-- Use this section for findings.  Leave empty if none. -->

### Blocking Issues

<!-- Format: [B-01] File:line — Description — Recommended fix -->

### Non-blocking Suggestions

<!-- Format: [S-01] File:line — Suggestion -->

---

## Approval

- [ ] All blocking issues resolved
- [ ] Ready to merge / accept
