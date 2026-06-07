# Tests

The test suite lives in `app/tests/` and runs **offline by default**—no AWS credentials, network access, or live LLM calls required for `make check`.

## Running tests

From the repository root:

```bash
make test          # pytest only
make check         # ruff + pytest (CI gate)
```

From `app/`:

```bash
uv run pytest
uv run pytest tests/test_doubt_solver_graph.py -v
uv run pytest -k "streaming" -v
```

## What is covered

| Area | Example test modules |
|---|---|
| Schemas | `test_schemas.py`, `test_doubt_solver_schemas.py`, `test_llm_schemas.py` |
| LangGraph workflows | `test_demo_graph.py`, `test_doubt_solver_graph.py`, `test_orchestrated_doubt_solver_graph_flow.py` |
| LLM orchestration | `test_llm_orchestrator.py`, `test_llm_route_resolver.py`, `test_model_execution_boundary.py` |
| Provider adapters | `test_azure_openai_provider_adapter.py`, `test_openai_provider_adapter.py`, `test_mock_provider_adapter.py` |
| Answer quality | `test_answer_quality.py`, `test_answer_completion.py` |
| Streaming | `test_orchestrated_streaming.py`, `test_streaming_adapter.py` |
| Classification & routing | `test_query_classifier_service.py`, `test_benchmark_model_routing.py` |
| Config & env | `test_config_validation.py`, `test_env_model_config_alignment.py` |
| Integration (mocked) | `test_integration_doubt_solver.py`, `test_main_routing.py` |

Fixtures and shared setup: `conftest.py`.

## Design principles

1. **Mock-first** — Use `MockProviderAdapter`, `MockModelExecutor`, and fake executors for unit tests.
2. **No secrets in tests** — Never hardcode API keys or real endpoints.
3. **Behavior over implementation** — Assert outputs, route decisions, and schema validity at service boundaries.
4. **Regression guards** — Empty-output handling, payload shaping for Azure reasoning models, and streaming contracts have dedicated tests.

## Opt-in live tests

Some Makefile targets and scripts exercise **real** providers when explicitly enabled:

- `make smoke-llm-orchestration-real` — requires `RUN_REAL_LLM_SMOKE=true` and provider credentials
- `make smoke-doubt-solver-real-llm` — manual end-to-end against a running `make dev` server

These are **not** part of `make check` or normal pytest collection.

## Adding tests

When changing behavior:

1. Add or update tests in the relevant `test_*.py` file.
2. Run `make check` before opening a PR.
3. Update `skills/features/<feature>.md` if the feature context documents test expectations.

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for full contribution guidelines.
