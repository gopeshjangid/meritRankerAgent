# Integration Boundaries — MeritRanker Tutor

> Rules for every external integration: databases, models, retrieval, cache, and APIs.
> Violation of these rules makes the system hard to test, hard to swap, and fragile.

---

## The Core Rule

> **Graph nodes must not import or call any external provider directly.**
> All external calls go through `app/services/`.

This applies without exception to: `boto3`, `anthropic`, `openai`, `google.cloud.*`,
`httpx`, `requests`, Redis clients, and any other I/O library.

---

## Service Boundary per Integration

| Integration | Service file | Status |
|---|---|---|
| Mock LLM response | `app/services/mock_response_service.py` | Active (demo graph only) |
| LLM model router | `app/services/model_router.py` | **Active** — use this for all LLM calls |
| LLM provider: mock | `app/services/llm_providers/mock_provider.py` | Active |
| LLM provider: Azure OpenAI | `app/services/llm_providers/azure_openai_provider.py` | Active (requires env vars) |
| LLM provider: OpenAI | `app/services/llm_providers/openai_provider.py` | Active (requires env vars) |
| DynamoDB question store | `app/services/dynamodb_question_service.py` | TODO |
| Bedrock Knowledge Base | `app/services/bedrock_kb_service.py` | TODO |
| Cache (Redis or in-memory) | `app/services/cache_service.py` | TODO (add only when needed) |

---

## Rules per Integration Type

### LLM / Model Calls

- All model calls go through a service (e.g., `bedrock_llm_service.py`).
- Graph nodes receive the service response and validate it with Pydantic before use.
- Do not put model provider SDK imports (`boto3`, `anthropic`, etc.) in graph node files.
- Provider-specific retry/throttle logic belongs inside the service, not the node.
- Model routing logic (which model for which request type) belongs in a routing service.
- `[AI RISK]` Model output is untrusted until schema-validated. A node must not act on raw model text.

### DynamoDB

- Access via a repository/service module in `app/services/`.
- Graph nodes call the service function — they never import `boto3.resource` or `boto3.client` directly.
- DynamoDB table names must come from env vars, not hardcoded strings.
- IAM permissions must be least-privilege — defined in `agentcore/agentcore.json` credentials block.
- Tests for DynamoDB service must use mocks or local DynamoDB — never real AWS in unit tests.
- `[PROD BLOCKER]` IAM scoping must be reviewed before production deployment.

### Bedrock Knowledge Base

- Access via `app/services/bedrock_kb_service.py`.
- Retrieved content is injected into prompts as context — never executed or trusted directly.
- Retrieved content must be treated as untrusted user-adjacent input. [AI RISK]
- Bound the number of retrieved passages per request to control cost. [PERFORMANCE RISK]
- Retrieval service must be mockable for tests.

### Cache (Redis or In-Memory)

- Do not add a cache before it is justified by a measured latency or cost problem.
- When added, access via `app/services/cache_service.py`.
- Cache invalidation strategy must be defined before implementation — not after.
- Cache must not store sensitive student data (PII, answers) without encryption plan. [SECURITY RISK]
- `[PERFORMANCE RISK]` Caching model output risks serving stale answers. Define TTL and invalidation policy.

### External HTTP APIs

- All external HTTP calls go through a dedicated service.
- Never call `requests.get(url)` or `httpx.get(url)` directly inside a graph node or tool.
- Timeouts must be set on every external call — no unbounded blocking. [PERFORMANCE RISK]
- Retry logic belongs in the service, not the graph node.

---

## Tools and Service Boundary

LangGraph tools in `app/tools/` may call services for infrastructure work.

**Allowed:**
```python
# app/tools/fetch_question_tool.py
def fetch_question(question_id: str) -> dict:
    return question_service.get_by_id(question_id)  # delegates to service
```

**Not allowed:**
```python
# app/tools/fetch_question_tool.py — WRONG
import boto3
def fetch_question(question_id: str) -> dict:
    table = boto3.resource("dynamodb").Table("questions")  # direct infra call
    ...
```

---

## Provider Lock-In Prevention

- No feature should lock the whole architecture to one provider.
- Provider selection must be driven by env var (e.g., `MODEL_PROVIDER=bedrock`).
- The service interface (function signature + return type) must not change when the provider changes.
- If a provider is the only viable choice, document it explicitly as `[ASSUMPTION]` and flag it for review if alternatives become available.

---

## Integration Testing

- Unit tests: mock the service. Graph nodes are tested with service mocks.
- Service tests: mock the provider SDK (e.g., `moto` for DynamoDB, `unittest.mock` for Bedrock).
- Integration tests against real AWS: only in dedicated integration test suites, never in `make check`. [NOT VERIFIED — integration test harness not yet defined]
