# Role Review Report: Backend Env Var Audit — Doubt Solver Local Setup

> Task: Audit and document all backend credentials/config required to run Doubt Solver locally
> Date: 2026-05-24
> Template: `skills/templates/` (solution-architect, security-reviewer, qa-reviewer,
>            documentation-maintainer, release-gate)

---

## A. Solution Architect Review

**Recommendation: PASS**

### Architecture boundary compliance

| Check | Result |
|---|---|
| All env vars loaded via `app/config.py` → `get_settings()` | PASS — confirmed in source |
| No credentials read in graph nodes directly | PASS — graph nodes call services only |
| No credentials read in `model_router.py` | PASS — routing reads config via `get_llm_role_config()` |
| AWS clients use only boto3 default credential chain | PASS — `aws_client_factory.py` uses `boto3.client()` with no hardcoded creds |
| `ENABLE_REAL_LLM=false` default ensures mock-only without credentials | PASS |
| `ENABLE_KB_RETRIEVAL=false` + `ENABLE_DYNAMODB_FETCH=false` defaults protect against unintended AWS calls | PASS |
| Per-service per-region client caching in `aws_client_factory.py` | PASS — prevents credential re-read per request |

### Config loading priority (verified in `config.py` docstring)

1. Real env vars (shell export, `agentcore dev` injection) — highest priority
2. `app/.env.local` (loaded via `python-dotenv`, `override=False`)
3. Hardcoded defaults in `get_settings()`

This order is correct.  `override=False` means the live environment always wins
over local file config, which is the safe default for deployed contexts.

### Gap identified and resolved

`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, and
`AWS_PROFILE` were absent from `app/.env.local.example`.  These are consumed by boto3's
credential chain but not by `config.py` directly.  This created a documentation gap
where developers enabling KB or DynamoDB would see configuration errors with no
guidance.  **Resolved:** AWS credential section added to both `app/.env.local.example`
and `app/.env.local`.

### Deferred items

- `[NOT VERIFIED]` IAM permission requirements for Bedrock KB and DynamoDB read access
- `[NOT VERIFIED]` Real DynamoDB table schema (primary key name `question_id` is assumed)
- `[DEFER]` Per-role region override (all AWS services currently share `AWS_REGION`)

---

## B. Security Reviewer

**Recommendation: PASS**

### Secrets handling

| Check | Result | Evidence |
|---|---|---|
| `app/.env.local` in `.gitignore` | PASS | Root `.gitignore` lines 26–28: `.env.local`, `app/.env.local` |
| `agentcore/.env.local` in `.gitignore` | PASS | `agentcore/.gitignore` line 2 |
| `app/.env.local` contains no real secrets | PASS | File reviewed — all values empty or default |
| `app/.env.local.example` contains no real secrets | PASS | File reviewed — all placeholder comments only |
| API keys not logged anywhere | PASS | `azure_openai_provider.py` and `openai_provider.py` log only `role` and `model_label` |
| Retrieved KB content not logged | PASS | `bedrock_kb_service.py` logs only `kb_id` and `result_count` |
| DynamoDB record content not logged | PASS | `dynamodb_service.py` logs only `table` name |
| Stream metadata enforces allowlist | PASS | `_sanitise_metadata()` + `_SAFE_METADATA_KEYS` in `streaming_adapter.py`; verified by `TestStreamingMetadataSafety` |
| No credentials hardcoded in Python source | PASS | grep for `sk-`, `AKIA`, `https://.*openai` in `app/` — no matches |

### Credential guidance added

- `app/.env.local.example` now includes AWS credential env vars with explicit
  `# WARNING: NEVER commit real AWS keys` comment.
- `docs/dev/backend-env.md` includes a Security notes section reiterating the
  logging and metadata safety guarantees.

### OWASP A02 (Cryptographic Failures / Sensitive Data Exposure)

No plaintext credentials in source, logs, or committed files.  Stream metadata
allowlist prevents accidental leakage through API responses.  **No issues found.**

### OWASP A05 (Security Misconfiguration)

Feature flags default to `false` — the safest possible default.  No AWS calls
are made unless explicitly enabled.  **No issues found.**

### [NOT VERIFIED] items

- `[NOT VERIFIED]` IAM policy attached to the execution role has least-privilege permissions
  for Bedrock KB and DynamoDB read operations.
- `[NOT VERIFIED]` No secrets appear in CloudWatch logs when deployed to AWS.

---

## C. QA Reviewer

**Recommendation: PASS**

### Test coverage for config validation

All missing-config paths are covered by `app/tests/test_config_validation.py`:

| Test class | Scenario | Tests |
|---|---|---|
| `TestLlmConfigValidation` | `ENABLE_REAL_LLM=true` + no role → `LlmConfigurationError` | 6 tests |
| `TestLlmConfigValidation` | Malformed JSON → `LlmConfigurationError` | included |
| `TestKbConfigValidation` | `ENABLE_KB_RETRIEVAL=true` + no KB ID → `KnowledgeBaseConfigurationError` | 3 tests |
| `TestKbConfigValidation` | Config error inside graph → `needs_review=True` | included |
| `TestDynamoDbConfigValidation` | `ENABLE_DYNAMODB_FETCH=true` + no table → `DynamoDbConfigurationError` | 3 tests |
| `TestDynamoDbConfigValidation` | Config error inside graph → `needs_review=True` | included |
| `TestDefaultConfigNoErrors` | All flags off → no errors | 5 tests |

Total: 17 config validation tests. All pass.

### CI gate

```
make check result: 572 passed, 0 failed, 1 warning (Pydantic v2 deprecation in third-party lib)
agentcore validate result: Valid
```

The warning is in `bedrock_agentcore/runtime/context.py` (third-party library) —
not in our code.  Not actionable.

### Manual smoke commands — [NOT VERIFIED]

All five smoke commands (`smoke-doubt-solver`, `smoke-doubt-solver-real-llm`,
`smoke-doubt-solver-with-retrieval`, `smoke-doubt-solver-combined`) require a
running `make dev` server and real credentials.  **Not verified in this audit.**
They are documented for manual execution.

---

## D. Documentation Maintainer

**Recommendation: Complete**

### Files created or updated

| File | Change | Status |
|---|---|---|
| `docs/dev/backend-env.md` | **Created** — canonical env var reference, all modes, security notes | Complete |
| `app/.env.local.example` | **Updated** — AWS credential section added with warning comment | Complete |
| `app/.env.local` | **Updated** — same AWS credential section (gitignored local copy) | Complete |
| `README.md` | **Updated** — sparse env var table replaced with full table + pointer to docs | Complete |
| `skills/features/doubt-solver.md` | **Updated** — env var / credentials section + mode table added; status updated | Complete |
| `Makefile` | **Updated** — `smoke-doubt-solver-combined` target added; `.PHONY` updated | Complete |

### Docs ↔ code alignment

- Every env var in `config.py` is now documented in `docs/dev/backend-env.md` ✅
- Every credential read in provider files is documented ✅
- Missing-config error messages in `docs/dev/backend-env.md` match exact strings in source ✅
- All `[NOT VERIFIED]` items are explicitly listed ✅

---

## E. Release Gatekeeper

**Final Decision: APPROVE WITH RISKS**

No new runtime code was added.  This is a documentation and tooling task.
All acceptance criteria are met.

### Evidence table

| Artefact | Received? | Notes |
|---|---|---|
| Solution Architect Review | Yes | PASS — gap identified and resolved |
| Security Review | Yes | PASS — no secrets in source or committed files |
| QA Review | Yes | PASS — 572 tests, 0 failures |
| Documentation Maintainer | Yes | Complete — all files updated |

### Blockers

None.

### Approved risks

| # | Risk | Label | Condition |
|---|---|---|---|
| 1 | IAM permissions for Bedrock KB + DynamoDB not audited | `[NOT VERIFIED]` | Requires live AWS account with real resources |
| 2 | Real LLM response quality not verified | `[NOT VERIFIED]` | Requires real Azure/OpenAI credentials |
| 3 | Real DynamoDB table schema not verified | `[NOT VERIFIED]` | `question_id` as PK is assumed |
| 4 | AgentCore HTTP streaming not implemented | `[NOT VERIFIED]` | Deferred to V2 |
| 5 | No production auth | `[PROD BLOCKER]` | Demo only — not for production |

### Next manual test steps

In priority order:

1. **Mock-only smoke** (no credentials):
   ```bash
   make dev   # separate terminal
   make smoke-doubt-solver
   ```
   Expected: JSON response with `"success": true`, `"answer_source": "mock"`, `"needs_review": false`.

2. **Real LLM smoke** (requires Azure OpenAI or OpenAI credentials):
   - Set `ENABLE_REAL_LLM=true`, `LLM_ROLE_CONFIG_JSON`, and provider credentials in `app/.env.local`.
   - `make dev` then `make smoke-doubt-solver-real-llm`.
   - Verify `"answer_source": "llm"` and coherent answer.

3. **KB retrieval smoke** (requires AWS + Bedrock KB):
   - Set `ENABLE_KB_RETRIEVAL=true`, `BEDROCK_KB_ID`, `AWS_REGION`, and AWS credentials.
   - `make dev` then `make smoke-doubt-solver-with-retrieval`.
   - Verify `"used_retrieval": true` and `"source_count" > 0`.

4. **DynamoDB smoke** (requires AWS + real tables):
   - Set `ENABLE_DYNAMODB_FETCH=true`, `DYNAMODB_QUESTION_TABLE`, `DYNAMODB_PATTERN_TABLE`.
   - `make dev` then `make smoke-doubt-solver-with-retrieval`.
   - Verify no `DynamoDbConfigurationError` in logs.

5. **Combined smoke** (all real services):
   - All vars from steps 2–4 combined.
   - `make smoke-doubt-solver-combined`.
   - Verify all three: `answer_source=llm`, `used_retrieval=true`, `source_count > 0`.

---

## Files reviewed (this audit)

- `AGENTS.md`
- `skills/roles/README.md`
- `skills/roles/solution-architect.md`
- `skills/roles/security-reviewer.md`
- `skills/roles/python-agent-engineer.md`
- `skills/roles/documentation-maintainer.md`
- `skills/core/security-and-privacy.md`
- `skills/core/integration-boundaries.md`
- `skills/features/doubt-solver.md`
- `app/config.py`
- `app/.env.local.example`
- `app/.env.local`
- `app/services/model_router.py`
- `app/services/llm_providers/azure_openai_provider.py`
- `app/services/llm_providers/openai_provider.py`
- `app/services/bedrock_kb_service.py`
- `app/services/dynamodb_service.py`
- `app/services/question_record_service.py`
- `app/services/aws_client_factory.py`
- `Makefile`
- `README.md`
- `.gitignore`

## Files changed (this audit)

| File | Change |
|---|---|
| `app/.env.local.example` | Added AWS credential env var section |
| `app/.env.local` | Added AWS credential env var section |
| `Makefile` | Added `smoke-doubt-solver-combined` target; updated `.PHONY` |
| `README.md` | Replaced sparse env var table with full table + pointer to backend-env.md |
| `skills/features/doubt-solver.md` | Added env var / credentials section; updated status line |
| `docs/dev/backend-env.md` | **Created** — canonical env var reference document |
| `skills/features/doubt-solver-v1-env-audit-release-gate.md` | **Created** — this report |
