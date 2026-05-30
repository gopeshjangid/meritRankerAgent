# Coding Standards — meritRankerTutor

> Permanent rules.  Every coding agent must follow these unless a task
> explicitly overrides a specific rule and justifies why.

---

## Language & Runtime

- **Python 3.11+** required.  Use modern syntax (`str | None`, `match`, etc.).
- Keep `requires-python = ">=3.11"` in `app/pyproject.toml`.
- Run with `uv` — never `pip` directly.

---

## Type Hints

- **Required for all public functions and methods.**
- Use built-in generic types (`list[str]`, `dict[str, int]`) not `List`, `Dict`.
- Use `X | None` not `Optional[X]`.
- Use `from __future__ import annotations` at the top of every module to allow
  forward references without quoting.
- Return type must always be annotated; `-> None` is explicit and required.

---

## Module Layout

```
app/
├── main.py            # Thin entrypoint only — no business logic here
├── config.py          # Settings singleton, env-var loading
├── logging_config.py  # configure_logging() and nothing else
├── graphs/            # One file per LangGraph workflow
├── schemas/           # One file per schema group (request, response, state)
├── services/          # One file per external integration
├── tools/             # One file per tool or tool group
├── prompts/           # One .md file per prompt template
└── tests/             # Mirror structure of app/ — test_<module>.py
```

**Rules:**
- `main.py` must stay thin: configure logging, build graph, define entrypoint, done.
- Graph nodes live in `graphs/`; they call services, never call external APIs directly.
- Services encapsulate all I/O.  One service = one external boundary.
- Tools are agent-callable functions only.  No DB calls, no raw HTTP in tool modules.
- Prompts are Markdown files loaded at runtime.  Never inline long prompts in `.py` files.

---

## Pydantic & Data Contracts

- Use **Pydantic v2** style throughout (`model_config`, `Field`, `model_dump()`).
- Every API boundary (request in, response out, graph state) has a Pydantic model.
- No large untyped `dict` values crossing module boundaries.
- Validate at the entrypoint (`main.py`), not deep inside graph nodes.
- Keep response shapes stable — breaking changes require explicit discussion and tests.

---

## Logging

- Always call `configure_logging()` from `app/logging_config.py` at startup.
- Use `logging.getLogger(__name__)` in every module.
- Log `request_id`, `user_id`, and `mode` at INFO level at request start and end.
- **Never log** secrets, API keys, full request payloads, or PII.
- Use `%s`-style formatting, not f-strings, in log calls (lazy evaluation).

---

## Error Handling

- Catch `pydantic.ValidationError` at the entrypoint and return a structured error response.
- Catch unexpected exceptions at the entrypoint; log them with `logger.exception()`.
- Never swallow exceptions silently inside graph nodes or services.
- Use specific exception types in `except` clauses; avoid bare `except:`.

---

## Code Style (Ruff)

- **Line length:** 100 characters.
- **Formatter:** `ruff format` (double quotes, 4-space indent).
- **Linter:** `ruff check` with `E, W, F, I, B, UP` rules enabled.
- Run `make fix` to auto-fix, `make lint` to check only.
- `ruff check` must pass with zero errors before any task is considered done.

---

## Testing

- Every new function / graph node / service method needs at least one pytest test.
- Tests live in `app/tests/` and follow `test_<module>.py` naming.
- Tests must run without AWS credentials, network access, or real LLM calls.
- Use mock services in tests; never call real external APIs in unit tests.
- `make check` (ruff + pytest) must pass before marking a task complete.

---

## Anti-patterns — Never Do These

| Anti-pattern | Why |
|---|---|
| Add FastAPI | AgentCore provides the HTTP layer |
| Hardcode secrets | Use env vars only |
| Call external APIs directly from graph nodes | Use services layer |
| Put application code in `agentcore/` | That directory is deploy config only |
| Use `pip install` | Use `uv add` |
| Add infra (DynamoDB, Redis, S3) without explicit task | Premature complexity |
| Large `dict` across module boundaries | Use Pydantic models |
| Skip tests for "quick fixes" | Every behavior change needs coverage |
| Change public schema silently | Breaking change — needs discussion |
| Use `.dict()` instead of `.model_dump()` | Pydantic v1 style, broken in v2 |
| Use f-strings in `logger.*` calls | Lazy evaluation prevents unnecessary string building |

---

## Labels for Code and Docs

Use these labels in comments, docs, and task outputs to flag conditions:

| Label | When to use |
|---|---|
| `[ASSUMPTION]` | A decision based on expected behaviour, not confirmed fact |
| `[NOT VERIFIED]` | A capability assumed but not confirmed in this runtime or environment |
| `[BLOCKER]` | An unresolved issue that blocks safe implementation |
| `[PROD BLOCKER]` | Must be resolved before production deployment |
| `[AI RISK]` | A risk from model, retrieval, prompt, or tool-use behaviour |
| `[SECURITY RISK]` | A potential security vulnerability or exposure |
| `[PERFORMANCE RISK]` | A likely latency or cost problem at scale |
| `[AUTH TODO]` | Auth not yet implemented — document explicitly, do not hide |
