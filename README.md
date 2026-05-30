# meritRankerTutor — AgentCore + LangGraph Agent

A clean local-first foundation for building a Python agent with
**Amazon Bedrock AgentCore** and **LangGraph**.

## Project Structure

```
meritRankerTutor/
├── AGENTS.md               # AI coding-assistant context (keep updated)
├── Makefile                # Dev commands — test, lint, format, dev, deploy
├── .gitignore
├── agentcore/              # AgentCore CLI / deployment config only
│   ├── agentcore.json      # Project config (runtimes, memories, gateways …)
│   ├── aws-targets.json    # Deployment targets (account + region)
│   ├── .env.local          # AgentCore secrets (gitignored)
│   └── cdk/                # CDK infrastructure (@aws/agentcore-cdk)
└── app/                    # All Python agent source code lives here
    ├── main.py             # AgentCore entrypoint
    ├── pyproject.toml      # Python deps + ruff + pytest config
    ├── config.py           # Settings (loaded from env / .env.local)
    ├── logging_config.py   # Rich-based readable logging
    ├── graphs/             # LangGraph workflow definitions
    │   └── demo_graph.py
    ├── schemas/            # Pydantic v2 models for request/response/state
    │   ├── request.py
    │   ├── response.py
    │   └── state.py
    ├── services/           # External integrations (swap mock → real later)
    │   └── mock_response_service.py
    ├── tools/              # LangGraph tool callables
    │   └── __init__.py
    ├── prompts/            # Prompt template files
    │   └── demo.md
    └── tests/              # pytest test suite
        ├── test_schemas.py
        └── test_demo_graph.py
```

## AI Coding Agent Context

This repo ships with repo-local documentation for AI coding agents
(Claude Code, Codex, GitHub Copilot, etc.) under `skills/`.

| Path | Contents |
|---|---|
| `AGENTS.md` | Primary instruction file — read this first |
| `skills/core/` | Coding standards, architecture rules, LangGraph patterns |
| `skills/features/` | Per-feature context (current state, schemas, tests) |
| `skills/roles/` | Role-specific behaviour guides (architect, QA, security…) |
| `skills/templates/` | Templates for feature docs, plans, reviews, bug reports |

**Rule:** When you change code, update the matching `skills/features/<name>.md`.
Docs and code must stay in sync.

---

## Getting Started

### Prerequisites

- **Node.js** 20.x or later
- **Python 3.10+** and **uv** for Python agents ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **AWS credentials** configured (`aws configure` or environment variables)
- **Docker** (only for Container build agents)

### Development

Run your agent locally:

```bash
agentcore dev
```

## Prerequisites

- **Python 3.11+** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 20+** (for AgentCore CLI)
- **AgentCore CLI** — `npm install -g @aws/agentcore`
- **AWS credentials** (only needed for `make deploy`)

## Quick Start

### 1 — Install Python dependencies

```bash
cd app
uv sync --group dev
```

### 2 — Verify environment

```bash
# from project root
make env
```

Expected output shows Python 3.11+, uv version, and agentcore version.

### 3 — Run tests

```bash
make test
```

### 4 — Run lint

```bash
make lint
```

### 5 — Start local agent server

```bash
make dev
```

AgentCore starts a local HTTP server (default **http://localhost:8080**).

### 6 — Send a test request

From another terminal:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "test local setup",
    "user_id": "local-user",
    "mode": "demo"
  }'
```

**Expected response:**

```json
{
  "success": true,
  "answer": "Hello! Local AgentCore + LangGraph setup is working. You said: test local setup",
  "request_id": "<uuid>",
  "mode": "demo"
}
```

> **Note:** If the AgentCore dev server uses a different path (e.g. `/invoke`), check the
> CLI output and adjust the curl URL accordingly.  Do not add FastAPI.

## Make Targets

| Target | Description |
|---|---|
| `make env` | Print Python, uv, and agentcore versions |
| `make test` | Run pytest |
| `make lint` | Ruff check (read-only) |
| `make format` | Ruff format in-place |
| `make fix` | Ruff check --fix + format |
| `make check` | lint + test (CI gate) |
| `make dev` | Start local AgentCore server |
| `make validate` | Validate agentcore.json |
| `make clean` | Remove cache / venv dirs |

## Environment Variables (`app/.env.local`)

Copy the example and customise:

```bash
cp app/.env.local.example app/.env.local
```

For the complete env var reference, missing-config error behaviour, and mode-by-mode
setup guides see [docs/dev/backend-env.md](docs/dev/backend-env.md).

Quick summary:

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `local` | Environment tag |
| `LOG_LEVEL` | `INFO` | Python log level |
| `ENABLE_REAL_LLM` | `false` | Master switch — `false` = mock LLM, no credentials needed |
| `LLM_ROLE_CONFIG_JSON` | `{}` | JSON map of role → provider config (required when `ENABLE_REAL_LLM=true`) |
| `AZURE_OPENAI_ENDPOINT` | _(empty)_ | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | _(empty)_ | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | _(empty)_ | Azure OpenAI API version string |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI native API key |
| `ENABLE_KB_RETRIEVAL` | `false` | Enable Bedrock Knowledge Base retrieval |
| `BEDROCK_KB_ID` | _(empty)_ | Bedrock KB ID (required when `ENABLE_KB_RETRIEVAL=true`) |
| `BEDROCK_KB_REGION` | _(AWS_REGION)_ | AWS region for Bedrock endpoint |
| `ENABLE_DYNAMODB_FETCH` | `false` | Enable DynamoDB record fetch |
| `DYNAMODB_QUESTION_TABLE` | _(empty)_ | DynamoDB table name for questions |
| `DYNAMODB_PATTERN_TABLE` | _(empty)_ | DynamoDB table name for patterns |
| `AWS_REGION` | _(boto3 chain)_ | Default AWS region (used by Bedrock + DynamoDB) |
| `DOUBT_SOLVER_MAX_CONTEXT_CHARS` | `6000` | Hard cap on context chars sent to LLM |

## LLM Orchestration Foundation

Part 4 adds a model execution boundary without enabling real provider calls:

- `ModelConfigResolver` resolves `RouteDecision.model` to model/provider metadata from
  the compiled registry.
- `RegistryBackedModelExecutor` builds an internal `ProviderExecutionRequest` and
  delegates to an injected `ProviderExecutor`.
- `FakeProviderExecutor` supports isolated tests only.
- Provider metadata is resolved, but secrets are not fetched and environment variables
  are not read.
- No Gemini, Azure OpenAI, OpenAI, AWS, or boto3 calls are made.
- No graph wiring, fallback execution, `SecretResolver`, or provider adapters are
  included in Part 4.

## Deploying to AWS

```bash
agentcore deploy
```

Requires AWS credentials and a configured `agentcore/aws-targets.json`.

## AgentCore CLI Reference

| Command | Description |
|---|---|
| `agentcore dev` | Run agent locally with hot-reload |
| `agentcore validate` | Validate agentcore.json schema |
| `agentcore deploy` | Deploy to AWS via CDK |
| `agentcore status` | Show deployment status |
| `agentcore invoke` | Invoke deployed agent |
| `agentcore logs` | View agent logs |
| `agentcore traces` | View agent traces |
