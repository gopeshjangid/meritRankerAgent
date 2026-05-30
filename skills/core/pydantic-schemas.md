# Pydantic Schemas — meritRankerTutor

> Rules for designing and maintaining Pydantic models in this project.

---

## File Layout

```
app/schemas/
├── __init__.py       # re-exports AgentRequest, AgentResponse, AgentState
├── request.py        # AgentRequest — inbound payload shape
├── response.py       # AgentResponse — outbound response shape
└── state.py          # AgentState — Python-layer graph state
```

Add new schema files as features grow:
```
├── question.py       # TODO: QuestionRequest / QuestionResponse
├── study_plan.py     # TODO: StudyPlanRequest / StudyPlanResponse
```

---

## Style Rules (Pydantic v2)

**Model configuration:**
```python
from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    user_id: str = Field(default="local-user", min_length=1, max_length=128)

    model_config = {"str_strip_whitespace": True}
```

- Use `model_config` dict, not the old `class Config`.
- Use `Field(...)` for required fields, `Field(default=...)` for optional.
- Add `description=` to every field — it documents the contract.
- Use `str_strip_whitespace = True` on request models to reject whitespace-only inputs.
- Serialise with `model_dump()`, not `.dict()` (Pydantic v1 style).
- Parse untrusted input with `Model.model_validate(data)`, not `Model(**data)`.

---

## Validation at the Boundary

Validate at the **entrypoint** (`main.py`) and trust types everywhere inside:

```python
# main.py — correct
request = AgentRequest.model_validate(payload)   # validate once

# graph node — correct (trusts the type)
def start_node(state: DemoGraphState) -> dict:
    log.info("user_id=%s", state["user_id"])      # no re-validation needed
```

Do **not** call `model_validate` inside graph nodes.

---

## Keeping Schemas Stable

Public schemas (`AgentRequest`, `AgentResponse`) are a contract with callers.

Rules:
- **Adding** an optional field with a default is backward-compatible.
- **Removing** or **renaming** a field is a breaking change — requires discussion.
- **Changing** a field type is a breaking change.
- When making a breaking change: add tests first, update docs, communicate clearly.

---

## Constraints Cheat-sheet

| Need | Pydantic v2 syntax |
|---|---|
| Non-empty string | `Field(..., min_length=1)` |
| Bounded string | `Field(..., min_length=1, max_length=5000)` |
| Positive int | `Field(..., gt=0)` |
| Enum-like string | `Literal["demo", "tutor"]` |
| Optional field | `str \| None = None` |
| Strip whitespace | `model_config = {"str_strip_whitespace": True}` |

---

## Tests for Schemas

Every schema module needs tests for:

- Valid input passes.
- Empty / whitespace-only strings are rejected.
- Values exceeding `max_length` are rejected.
- Missing required fields raise `ValidationError`.
- `model_dump()` produces the expected dict.

See `app/tests/test_schemas.py` for examples.

---

## Validate External Output

**[AI RISK]** Model output, tool call results, and external service responses must be
validated at the **receiving boundary** — the node or service that gets the response.

```python
# services/bedrock_llm_service.py
def invoke(prompt: str) -> LLMResponseSchema:
    raw = bedrock_client.invoke(...)
    return LLMResponseSchema.model_validate(raw)  # validate inside service

# graph node
def respond_node(state: DemoGraphState) -> DemoGraphState:
    result = llm_service.invoke(state["message"])  # already validated
    return {**state, "answer": result.text}         # safe to use
```

Rules:
- Each service function returns a Pydantic model, never a raw dict or raw string.
- The graph node trusts the returned type (as with inbound requests).
- If the external output does not match the schema, catch `ValidationError` in the service
  and raise a domain-specific exception that the node can handle.
- `max_length` constraints must be set on model output fields to prevent oversized responses
  from propagating through the graph.

