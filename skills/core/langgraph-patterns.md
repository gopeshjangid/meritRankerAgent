# LangGraph Patterns — meritRankerTutor

> Conventions for building, testing, and extending LangGraph workflows in this project.

---

## Graph File Naming

One file per workflow, named after the feature:

```
app/graphs/
├── demo_graph.py           # local demo / foundation
├── question_solver_graph.py  # TODO: question answering workflow
├── study_plan_graph.py       # TODO: study plan generation workflow
└── __init__.py
```

**Rule:** Never put two unrelated workflows in one file.

---

## State Schema

Every graph defines a `TypedDict` for its internal state:

```python
from typing import TypedDict

class DemoGraphState(TypedDict):
    request_id: str
    message: str
    user_id: str
    mode: str
    answer: str | None
```

**Why TypedDict instead of Pydantic?**  LangGraph's reducer and checkpointer system
works most reliably with plain dicts.  Pydantic models are used at the API boundary
(`main.py`) only.  `main.py` converts `AgentState` ↔ graph dict.

---

## Node Functions

Each node is a plain Python function that:
- Receives the full state dict.
- Returns a **partial update dict** (only the keys it changes).
- LangGraph merges the returned dict into the current state.

```python
def respond_node(state: DemoGraphState) -> dict:
    answer = some_service.generate(state["message"])
    return {"answer": answer}   # only return what changed
```

**Rules:**
- Nodes must be **deterministic** where possible — same input → same output.
- Nodes call **services** or **tools**, never external APIs or SDKs directly.
- Keep nodes small (< 30 lines ideally).  Extract helpers if needed.
- Log `request_id` and the node name at DEBUG level.

---

## Graph Construction

Build and compile the graph in a factory function:

```python
from langgraph.graph import END, START, StateGraph

def build_demo_graph():
    builder = StateGraph(DemoGraphState)

    builder.add_node("start_node", start_node)
    builder.add_node("respond_node", respond_node)

    builder.add_edge(START, "start_node")
    builder.add_edge("start_node", "respond_node")
    builder.add_edge("respond_node", END)

    return builder.compile()
```

- **Compile once at startup** (in `main.py`), not per request.
- The compiled graph is thread-safe and reusable.
- Expose only `build_<feature>_graph()` from each graph module.

---

## Conditional Routing

Use conditional edges only when the workflow genuinely branches:

```python
def route_by_mode(state: GraphState) -> str:
    if state["mode"] == "quick":
        return "fast_node"
    return "deep_node"

builder.add_conditional_edges("entry_node", route_by_mode)
```

Do not add conditional routing "just in case" — add it when the branch exists.

---

## Validate Model and Tool Output Before Trusting It

**[AI RISK]** Model output, tool call results, and external service responses are
**untrusted** until schema-validated. A graph node must never act on raw string
model output for routing decisions or state updates without validation.

```python
def respond_node(state: DemoGraphState) -> DemoGraphState:
    raw_result = llm_service.invoke(state["message"])
    validated = LLMResponseSchema.model_validate(raw_result)   # validate first
    return {**state, "answer": validated.text}                  # then use
```

For routing decisions based on model output, validate against an explicit allowlist:

```python
ALLOWED_ROUTES = {"hint", "explain", "quiz"}
route = validated.next_action
if route not in ALLOWED_ROUTES:
    logger.warning("Unexpected route from model: %s", route)
    route = "hint"  # safe default
```

---

## Error Handling in Nodes

Nodes should not catch errors they cannot meaningfully handle.
Let exceptions propagate to `main.py` which catches them centrally:

```python
# main.py
except Exception as exc:
    logger.exception("request_id=%s — unexpected error", request_id)
    return {"success": False, "answer": f"Internal error: {exc}", ...}
```

---

## Testing Graphs

Graphs must be testable without the AgentCore runtime:

```python
def test_graph_produces_answer():
    graph = build_demo_graph()
    result = graph.invoke({
        "request_id": "test-001",
        "message": "hello",
        "user_id": "test-user",
        "mode": "demo",
        "answer": None,
    })
    assert result["answer"] is not None
```

- Import and call the graph directly — no HTTP, no AgentCore server.
- Mock services at the module level if needed (use `monkeypatch` or `unittest.mock`).
- Test each edge case: empty inputs, error paths, conditional routing branches.

---

## Future Patterns (TODO)

When real features are implemented, add examples for:

- [ ] Tool-calling nodes (LangGraph `ToolNode`)
- [ ] Memory injection (passing session context into state)
- [ ] Streaming responses
- [ ] Parallel fan-out nodes
- [ ] Checkpointing / resumable workflows
