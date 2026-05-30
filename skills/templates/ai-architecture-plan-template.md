# AI Architecture Plan: <feature name>

> Role: AI Solution Architect
> Template: `skills/templates/ai-architecture-plan-template.md`
> Instruction: Fill every section. This plan is reviewed alongside the Solution Architect plan.
> No code is written until both plans are aligned.
> Delete this instruction block before submitting.

---

## AI Workflow Plan

<!-- Describe the high-level AI workflow in plain language.
     What does the agent/graph do from input to output?
     How many steps, models, or tool calls are involved? -->

---

## Graph Design

<!-- Describe the LangGraph nodes, edges, and routing logic. -->

| Node | Type | Purpose |
|---|---|---|
| `<node_name>` | Standard / Tool / Conditional | |

**Edges:**

```
START → <node_a> → <node_b> → END
```

**Conditional routing (if any):**

> <!-- Describe routing conditions and the allowlist of valid outcomes.
>      All model-driven routing must validate against an explicit allowlist. [AI RISK] -->

---

## Prompt / Model / Retrieval Boundaries

<!-- For each model call or retrieval call, specify: -->

| Step | Type | Model / Source | Input | Output | Boundary |
|---|---|---|---|---|---|
| `<node>` | LLM / KB retrieval | `<model or KB name>` | `<what is sent>` | `<what is expected>` | `app/services/<name>.py` |

**[AI RISK]** All model output and retrieved content is untrusted until schema-validated.
Confirm each boundary above has a Pydantic schema at the receiving end.

---

## Tool Boundaries

<!-- List all LangGraph tools. Tools must delegate to services for infrastructure. -->

| Tool | File | Purpose | Delegates to service? |
|---|---|---|---|
| | `app/tools/<name>_tool.py` | | Yes / No / N/A |

<!-- If no tools: write "No tools used." -->

---

## State / Schema Additions

<!-- List all new or changed LangGraph state fields and Pydantic schemas. -->

| Name | Type | Location | Purpose |
|---|---|---|---|
| `<field>` | `str \| None` | `<GraphState>` TypedDict | |

<!-- Confirm state fields do not contain raw model output — only validated values. -->

---

## Hallucination Risks

<!-- Where could the model produce incorrect, fabricated, or misleading output?
     How is each risk mitigated? -->

| Risk | Mitigation | Label |
|---|---|---|
| Model returns incorrect answer | Schema validation + fallback response | [AI RISK] |
| Model returns malformed structure | Pydantic `model_validate()` at service boundary | [AI RISK] |
| | | |

---

## Prompt-Injection Risks

<!-- Where does user-supplied or retrieved content enter the prompt?
     How is it isolated from system instructions? -->

| Prompt section | Content source | Injection risk | Mitigation |
|---|---|---|---|
| System role | Hard-coded template | Low | Keep user content out of system role |
| User role | User `message` field | Medium | Bounded by max_length in schema |
| Context block | Retrieved KB passages | High | Delimited `<context>...</context>`; [AI RISK] |

---

## Output Validation Strategy

<!-- For every node that acts on model or tool output, describe the validation. -->

| Node | Output type | Validation method | On validation failure |
|---|---|---|---|
| `<node>` | `<SchemaName>` | `model_validate()` in service | Return error state / safe default |

---

## Evaluation / Test Strategy

<!-- How will the AI behaviour be tested without real model calls? -->

| Test | File | Type | Mock used |
|---|---|---|---|
| Graph produces answer for valid input | `app/tests/test_<name>.py` | Unit | `monkeypatch` service |
| Routing produces valid route | `app/tests/test_<name>.py` | Unit | Fixed model mock output |
| Validation failure on bad model output | `app/tests/test_<name>.py` | Unit | Mock returns invalid format |

**[NOT VERIFIED]** if evaluation against real model output has not been tested.

---

## Model / Provider Requirements

| Requirement | Value | Status |
|---|---|---|
| Model provider | | Active / TODO / [NOT VERIFIED] |
| Model name | | Active / TODO / [NOT VERIFIED] |
| Context window required | | [ASSUMPTION] if not confirmed |
| Tool-calling support needed | Yes / No | |

---

## Latency / Cost Notes

| Factor | Estimated value | Label |
|---|---|---|
| Model calls per request | | [PERFORMANCE RISK] if > 1 |
| Retrieval calls per request | | [PERFORMANCE RISK] if unbounded |
| Prompt tokens per request | | [COST RISK] if unbounded |
| Total user-facing latency | | [PERFORMANCE RISK] if > threshold |

---

## Observability Plan

<!-- How will AI behaviour be monitored in production? -->

| Signal | Implementation | Status |
|---|---|---|
| Request latency per node | `logger.debug` at node entry/exit | [NOT VERIFIED — not yet implemented] |
| Model call success/failure | Logged in service | [NOT VERIFIED — service not yet built] |
| Validation failure rate | Logged at WARNING level | [NOT VERIFIED] |

---

## Clarification / Escalation Plan

<!-- What should the engineer do if they encounter an unexpected AI behaviour during implementation? -->

- If model output consistently fails schema validation → escalate to AI Solution Architect before workaround.
- If prompt-injection risk is identified in retrieved content → escalate to Security Reviewer before release.
- If routing logic requires more than 3 conditional branches → escalate to Solution Architect for graph redesign.
- [REQUIRES ARCHITECT ALIGNMENT] if model provider or model name must change from this plan.

---

## Open Issues

<!-- List unresolved issues that block or risk this AI design. -->

| # | Issue | Label | Status |
|---|---|---|---|
| 1 | | [BLOCKER] / [AI RISK] / [NOT VERIFIED] | Open |
