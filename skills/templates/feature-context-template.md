# Feature: <name>

> Template: `skills/templates/feature-context-template.md`
> Copy to `skills/features/<feature-name>.md` when starting a new feature.
> Fill every section. Use [NOT VERIFIED] or [DOCS TODO] if a fact is unknown.
> **No mandatory section should be empty.**
> Delete this instruction block before committing.

---

## Purpose

<!-- What does this feature do, and for whom? 1–3 sentences. -->

---

## Current Status

<!-- One of: Demo | In Progress | Production | Deprecated | Removed -->

---

## User Flow

<!-- Step-by-step description of what the user experiences, in plain language. -->

1. User ...
2. System ...
3. User receives ...

---

## Entrypoints

| File | Function | Description |
|---|---|---|
| `app/main.py` | `invoke(payload: dict) -> dict` | <!-- How this feature is triggered --> |

<!-- Include the request → graph → response flow if non-trivial. -->

---

## Graphs

| File | Builder function | Nodes |
|---|---|---|
| `app/graphs/<name>_graph.py` | `build_<name>_graph()` | `node_a → node_b → ...` |

**Node descriptions:**

| Node | Behaviour |
|---|---|
| `node_a` | <!-- What it does --> |
| `node_b` | <!-- What it does --> |

**Internal state type:** `<FeatureName>GraphState` (TypedDict)

---

## Schemas

| File | Model | Purpose |
|---|---|---|
| `app/schemas/request.py` | `AgentRequest` | Validates inbound payload |
| `app/schemas/response.py` | `AgentResponse` | Structures outbound response |

<!-- Add feature-specific schemas if applicable. -->

---

## Services

| File | Function | Description |
|---|---|---|
| `app/services/<name>_service.py` | `<function>()` | <!-- What it does, what it integrates with --> |

<!-- If no services: write "None." -->

---

## Tools

<!-- List LangGraph tools used, or write "None." -->

---

## Prompts

| File | Use |
|---|---|
| `app/prompts/<name>.md` | <!-- Which node uses this prompt --> |

<!-- Or write "None." -->

---

## Tests

| File | Covers |
|---|---|
| `app/tests/test_<name>.py` | <!-- Summarise test scenarios covered --> |

---

## Config / Env

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `local` | Environment tag |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `MODEL_PROVIDER` | `mock` | Which model backend to use |

<!-- Add feature-specific env vars here. -->

---

## Known Limitations

<!-- Be honest. Every feature has limitations at creation time.
     Use [NOT VERIFIED], [AUTH TODO], [PROD BLOCKER], [DEFER] labels. -->

- [AUTH TODO] No authentication or authorisation implemented.
- [NOT VERIFIED] <!-- Any capability assumed but not confirmed. -->
- <!-- Add any others. -->

---

## Latest Changes

<!-- Most recent entry first. Add an entry every time this feature changes. -->

- `YYYY-MM-DD` — Initial implementation.

---

## Next Steps

<!-- What is planned but not yet implemented?
     Use [DEFER] for items intentionally postponed.
     Use [BLOCKER] for items that cannot proceed without resolution. -->

- [ ] ...
- [ ] [DEFER] ...

<!-- Optional but recommended. -->

- [ ] Connect real LLM service
- [ ] Add authentication
