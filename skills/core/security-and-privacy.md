# Security and Privacy — MeritRanker Tutor

> Security and privacy rules that apply to every role and every task.
> These are not optional. A change that violates these rules must be fixed before release.

---

## Secrets

**Do not put secrets anywhere in the repository.**

This includes:
- Python source files (`app/**/*.py`)
- Markdown files (`skills/**/*.md`, `README.md`, `AGENTS.md`, prompt templates)
- Test files (`app/tests/**`)
- AgentCore config (`agentcore/agentcore.json`, `agentcore/aws-targets.json`)
- Log output

**Where secrets belong:**
- `app/.env.local` — local developer secrets (must be in `.gitignore`)
- AWS Secrets Manager or Parameter Store — production secrets
- AgentCore credential resources — provider API keys at deploy time

**Pattern to avoid:**
```python
# WRONG — never do this
API_KEY = os.getenv("OPENAI_API_KEY", "sk-1234hardcodedkey")
```

---

## Authentication and Trust

**The current system has no authentication. This is a known limitation.**

- Do not trust frontend-supplied `user_id`, `student_id`, or `session_id` for any
  access control or personalisation decisions in production. [PROD BLOCKER]
- Any flow that relies on client-supplied identity without server-side verification
  must be labelled `[AUTH TODO]` in the feature context doc.
- Missing auth must not be silently accepted — it must be documented and flagged.

**Future auth:** JWT validation, Cognito, or AgentCore gateway auth will be added in
a later phase. Do not implement auth prematurely — document the gap instead.

---

## Logging

**Never log the following:**
- Secrets or API keys (any partial or full value)
- Full request payloads (including `message` field at INFO level or above)
- Full retrieved document content
- Full prompt text sent to a model
- Student PII (full name, email, student ID, assessment scores)
- Internal tracebacks in responses sent to callers

**What to log at INFO level:**
- `request_id`, `user_id`, `mode` at request start and end
- Service call outcomes (success/failure, latency if measured)
- Error type and message — not the full raw exception payload to callers

**What to log at DEBUG level:**
- Node entry/exit with `request_id`
- Intermediate state fields (avoid fields that contain PII or model output)

---

## Input Validation

- All inbound payloads are validated by Pydantic at the `invoke()` entrypoint.
- Pydantic models on user-supplied string fields must have `max_length` constraints.
- `str_strip_whitespace = True` must be set on request models.
- After Pydantic validation, inner layers trust the type — no re-validation inside nodes.

---

## Untrusted Content

The following are **untrusted** until validated by your code:

| Source | Risk | Mitigation |
|---|---|---|
| Inbound request payload | Malformed, oversized, injected | Pydantic validation at boundary |
| Model output | Hallucinated, malformed, injected instructions | Schema validation before use |
| Retrieved KB / RAG context | Prompt injection, misleading content | Isolate from system prompt; validate before use |
| Tool call results | Unexpected format, injected content | Schema validation before use |
| Client-supplied user identity | Unverified | `[AUTH TODO]` — not used for access control |

**[AI RISK]** Retrieval-augmented content sourced from user-adjacent data (e.g.,
student notes, forum posts) has elevated prompt-injection risk. It must be injected
into the prompt as clearly delimited context, not as system instructions.

---

## Prompt-Injection Risks

- Retrieval results and user-supplied content must be placed in clearly delimited
  sections of the prompt (e.g., `<context>...</context>`), never in the system role.
- Prompt templates must be reviewed for instruction-injection surfaces before production.
- `[AI RISK]` If model output is used to select the next tool or node, the routing logic
  must validate the output against a strict allowlist of valid choices.

---

## External Calls

- All external calls go through `app/services/` (see `integration-boundaries.md`).
- Never construct and execute shell commands from user input. [SECURITY RISK]
- Never use `eval()`, `exec()`, or `subprocess` with user-controlled strings. [SECURITY RISK]
- Never use `pickle` to deserialise untrusted data. [SECURITY RISK]

---

## PII and Privacy

- Student messages and responses are potentially sensitive. Treat them as PII.
- Do not persist student conversation data without a defined data retention policy. [PROD BLOCKER]
- Do not send student data to third-party providers without confirming data processing terms. [PROD BLOCKER]
- PII handling requirements must be documented in the relevant feature context under `## Known Limitations` or `## Config / Env`.

---

## IAM and Cloud Permissions

- Use least-privilege IAM roles for all AWS resources.
- DynamoDB, Bedrock, S3, and other resource access must be scoped to the minimum needed.
- IAM boundaries are defined in `agentcore/agentcore.json` credentials block.
- `[PROD BLOCKER]` IAM policies must be reviewed before deploying to production.

---

## OWASP Top 10 Quick Reference

| Risk | How it applies here |
|---|---|
| A01 Broken Access Control | No auth yet — `[AUTH TODO]` for every user-identity-dependent flow |
| A02 Cryptographic Failures | Secrets in env vars, never in source |
| A03 Injection | Pydantic validation; no `eval`/`exec`/`subprocess` with user input |
| A05 Security Misconfiguration | Debug logs and verbose tracebacks off in production |
| A06 Vulnerable Components | Review `uv.lock` for known CVEs before production deployment |
| A07 Auth Failures | Tokens/sessions not yet validated — document explicitly |
| A09 Logging Failures | No secrets, no PII, no full payloads in logs |
