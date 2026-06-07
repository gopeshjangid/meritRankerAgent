# Examples

This directory documents how to run and exercise MeritRanker Agent Python workflows. There are no standalone example scripts here yet—the project uses Makefile smoke targets and the local AgentCore HTTP API instead.

## Mock mode (recommended first)

No API keys or AWS credentials required.

```bash
# Terminal 1 — start the agent
make dev

# Terminal 2 — smoke test doubt solver
make smoke-doubt-solver
```

## Demo mode

Simple hello-world graph for verifying AgentCore + LangGraph wiring:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "test local setup",
    "user_id": "local-user",
    "mode": "demo"
  }'
```

## Doubt solver (structured tutoring flow)

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "doubt_solver",
    "query": "Explain blood relation problems with a simple example.",
    "user_id": "example-user",
    "language": "en"
  }'
```

Enable the orchestrated path (recommended for current development):

```bash
# In app/.env.local
ENABLE_ORCHESTRATED_DOUBT_SOLVER=true
```

Restart `make dev` after changing environment variables.

## LLM orchestration dry-run

Exercises route resolution and mock provider execution without network I/O:

```bash
make smoke-llm-orchestration-mock
```

Equivalent script (from repository root):

```bash
cd app && uv run python scripts/smoke_llm_orchestration.py --help
```

## Real provider smoke tests (opt-in)

These require credentials in `app/.env.local` or your shell environment. **Do not commit secrets.**

```bash
# Doubt solver with real LLM (make dev must be running)
make smoke-doubt-solver-real-llm

# Direct orchestration smoke
RUN_REAL_LLM_SMOKE=true OPENAI_API_KEY=... make smoke-llm-orchestration-real
```

See [docs/dev/backend-env.md](../docs/dev/backend-env.md) for required variables per provider.

## Streaming

When streaming is enabled for doubt solver, the entrypoint may return a generator of stream events rather than a single JSON body. Consult `app/services/doubt_solver/streaming_doubt_solver_service.py` and `app/schemas/doubt_solver.py` for event shapes.

Integration tests in `app/tests/test_orchestrated_streaming.py` cover streaming behavior in offline mock mode.

## Next steps

- Read [README.md](../README.md) for full setup
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) before opening a PR
- Explore prompt templates in `app/prompts/subjects/` and routes in `app/config/llm/llm_routes.yaml`
