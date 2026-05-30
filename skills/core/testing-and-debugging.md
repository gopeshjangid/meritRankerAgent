# Testing and Debugging — meritRankerTutor

> Strategy for writing tests, running quality gates, and debugging locally.

---

## CI Gate — Must Always Pass

```bash
make check
```

This runs, in order:
1. `uv run ruff check .` — lint (zero errors required)
2. `uv run pytest` — all tests must pass

**Run `make check` before marking any task complete.**

---

## Test Layout

```
app/tests/
├── __init__.py
├── test_schemas.py        # Pydantic model validation tests
├── test_demo_graph.py     # LangGraph graph integration tests
└── test_<module>.py       # Mirror the module under test
```

**Rules:**
- Test file name: `test_<module_being_tested>.py`.
- Test class name: `Test<Subject>` (e.g., `TestAgentRequest`).
- Test function name: `test_<what_and_expected_outcome>` (e.g., `test_empty_message_fails`).
- One assertion per test function where possible.

---

## Testing Layers

### 1. Schema tests (`test_schemas.py`)
- Validate valid inputs pass.
- Validate invalid inputs raise `ValidationError`.
- Verify `model_dump()` output shape.

### 2. Graph tests (`test_<feature>_graph.py`)
- Call `build_<feature>_graph()` directly — no HTTP, no AgentCore runtime.
- Verify output state contains expected fields.
- Verify `request_id` is preserved.
- Verify answer contains key content from the input message.

### 3. Service tests (`test_<feature>_service.py`) — add when real services exist
- Test with a mock or stub of the external dependency.
- Never call real APIs (Bedrock, DynamoDB, etc.) in unit tests.

### 4. Integration tests (TODO)
- Full `invoke()` round-trip with `TestClient` or mock AgentCore harness.
- Add once the local test harness pattern is established.

---

## Mocking Strategy

- Use `unittest.mock.patch` or `pytest` fixtures for mocking services.
- Mock at the service boundary — do not mock graph nodes directly.

```python
# Example: mock a service in a graph test
from unittest.mock import patch

def test_graph_with_mocked_service():
    with patch("services.mock_response_service.generate_mock_response") as mock_fn:
        mock_fn.return_value = "mocked answer"
        graph = build_demo_graph()
        result = graph.invoke({...})
        assert result["answer"] == "mocked answer"
```

---

## Mocking Strategy

- Use `unittest.mock.patch` or `pytest` fixtures for mocking services.
- Mock at the service boundary — do not mock graph nodes directly.

```python
# Example: mock a service in a graph test
from unittest.mock import patch

def test_graph_with_mocked_service():
    with patch("services.mock_response_service.generate_mock_response") as mock_fn:
        mock_fn.return_value = "mocked answer"
        graph = build_demo_graph()
        result = graph.invoke({...})
        assert result["answer"] == "mocked answer"
```

---

## Regression Tests

Every bug fix must include a regression test:

- Add a test that **fails before the fix** and **passes after the fix**.
- The test name should describe the bug: `test_empty_message_returns_validation_error`.
- Do not mark regression tests as skipped — they must run in `make check`.
- The regression test goes in the same test file as the feature it covers.

---

## When Tests Cannot Run — [NOT VERIFIED]

If a test requires infrastructure that does not exist locally (DynamoDB, Bedrock,
Knowledge Base), do **not** delete the test or leave it uncovered silently.

**Instead:**
```python
import pytest

@pytest.mark.skip(reason="[NOT VERIFIED] — requires DynamoDB table, not available locally")
def test_question_fetch_from_db():
    ...
```

Rules:
- The `[NOT VERIFIED]` label must appear in the `reason` string.
- The test must still be implemented (even if skipped) so the intent is captured.
- When the infra becomes available, remove the skip and verify the test passes.
- `[NOT VERIFIED]` tests must be listed in the feature context doc under `## Known Limitations`.

---

## Debugging Locally

### Step 1 — Check logs from `make dev`

```bash
make dev   # starts agentcore dev --logs
```

Rich-formatted logs include `request_id`, module name, and log level.
Set `LOG_LEVEL=DEBUG` in `app/.env.local` for verbose output.

### Step 2 — Run a single test with output

```bash
cd app && uv run pytest tests/test_demo_graph.py -v -s
```

### Step 3 — Run pytest with full traceback

```bash
cd app && uv run pytest --tb=long
```

### Step 4 — Invoke the graph directly in a Python REPL

```bash
cd app && uv run python
>>> from graphs.demo_graph import build_demo_graph
>>> g = build_demo_graph()
>>> g.invoke({"request_id": "debug", "message": "hi", "user_id": "u1", "mode": "demo", "answer": None})
```

---

## Logging Rules

- Log `request_id` on every request start and end (INFO level).
- Log graph node entry at DEBUG level.
- **Never log** secrets, tokens, full payloads, or PII.
- Use `%s`-style format strings in log calls (not f-strings).

```python
logger.info("request_id=%s  user_id=%s  mode=%s — invoke started",
            request_id, request.user_id, request.mode)
```

---

## Common Failures and Fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ImportError: No module named 'schemas'` | pytest not running from `app/` | `cd app && uv run pytest` |
| `ModuleNotFoundError: bedrock_agentcore` | venv not set up | `cd app && uv sync --group dev` |
| `ValidationError` on a valid request | Whitespace-only value | Check `str_strip_whitespace` |
| Graph returns `None` for answer | `respond_node` not reached | Check edge wiring in `build_*_graph()` |
| `ruff: 1 error` on import order | isort order wrong | Run `make fix` to auto-correct |

---

## TODO — Future Testing Strategy

- [ ] Add `conftest.py` with shared fixtures (e.g., sample `AgentRequest`)
- [ ] Add integration test harness using a mock HTTP client
- [ ] Add coverage reporting: `uv run pytest --cov=. --cov-report=term-missing`
- [ ] Add CI workflow (GitHub Actions / CodeBuild) that runs `make check`
