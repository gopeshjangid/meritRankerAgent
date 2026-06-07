# Contributing to MeritRanker Agent Python

Thank you for your interest in contributing. This project is early-stage and actively developed. We welcome focused improvements that align with education-focused AI agent workflows.

## Before you start

- Read [README.md](README.md) for project scope and setup.
- Read [AGENTS.md](AGENTS.md) for repository boundaries and coding rules.
- For deeper context, see `skills/core/` and the relevant file under `skills/features/`.

## Development setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management
- Node.js 20+ and the [AgentCore CLI](https://www.npmjs.com/package/@aws/agentcore) for local runtime and deployment config validation

### Install

```bash
cd app
uv sync --group dev
```

Copy environment defaults (no secrets required for mock mode):

```bash
cp app/.env.local.example app/.env.local
```

Verify tooling from the repository root:

```bash
make env
make check
agentcore validate
```

## Branch naming

Use short, descriptive branch names:

| Prefix | Use for |
|---|---|
| `feat/` | New features or workflows |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `test/` | Test additions or fixes |
| `refactor/` | Internal restructuring without behavior change |
| `chore/` | Tooling, CI, dependency updates |

Examples: `feat/doubt-solver-streaming`, `fix/azure-payload-shaping`, `docs/readme-quickstart`.

## Testing

All tests run without AWS credentials or network access unless explicitly marked otherwise.

```bash
make test          # pytest only
make check         # ruff + pytest (CI gate)
```

Guidelines:

- Add or update tests for every behavior change.
- Prefer unit tests with mocks over live provider calls.
- Do not commit secrets or enable real LLM tests in CI by default.
- Opt-in smoke targets (`make smoke-doubt-solver-real-llm`, etc.) are for manual verification only.

## Pull request expectations

1. **Scope** — One logical change per PR when possible.
2. **Quality gate** — `make check` and `agentcore validate` must pass.
3. **Schemas** — Public request/response shapes use Pydantic v2 in `app/schemas/`. Avoid breaking changes without discussion.
4. **Boundaries** — Application code stays in `app/`. Deployment config stays in `agentcore/`. Do not add FastAPI or move Python into `agentcore/`.
5. **Secrets** — Never commit API keys, `.env.local`, or real credentials.
6. **Description** — Explain what changed, why, and how you tested it.

## Code quality

- **Lint/format:** Ruff (`make lint`, `make format`, `make fix`).
- **Typing:** Use type hints on public functions and service boundaries.
- **Logging:** Call `configure_logging()` before logging. Do not log secrets, full prompts, or full private payloads.
- **Services:** External integrations belong in `app/services/`. Graph nodes call services; they do not call providers directly.
- **Prompts:** Store templates in `app/prompts/` as Markdown files.

## Documentation updates

When you change behavior, update the matching feature context:

- Feature docs: `skills/features/<feature-name>.md`
- Developer env reference: `docs/dev/backend-env.md` (when env vars change)
- Public docs: `README.md`, `ROADMAP.md`, or `examples/README.md` when user-facing workflow changes

If documentation and code disagree, the change is not complete.

## Questions

Open a GitHub issue for bugs, design questions, or proposed features. For security concerns, see [SECURITY.md](SECURITY.md).
