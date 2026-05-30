# Performance-Cost Review: <feature / task name>

> Role: Performance-Cost Reviewer
> Template: `skills/templates/performance-cost-review-template.md`
> Instruction: Fill every section based on evidence only.
> Count every network/model/retrieval call on the user-facing path.
> Refer to `skills/core/performance-and-scalability.md` for project rules.
> Delete this instruction block before submitting.

---

## Recommendation

<!-- Choose exactly one: PASS | PASS WITH NOTES | FAIL | BLOCK -->

**PASS WITH NOTES**

<!-- Replace with actual recommendation above. Reason in Final Decision Reason section. -->

---

## Execution Type

<!-- Describe the request profile: synchronous / streaming / background -->

**Type:** Synchronous / Streaming / Background  
**User-facing?** Yes / No  
**Per-request or batch?** Per-request / Batch

---

## Critical Path

<!-- List every step on the synchronous user-facing path, in order. -->

| Step | Type | Blocking? |
|---|---|---|
| Input validation (Pydantic) | CPU | Yes |
| `<node_name>` | Graph node | Yes |
| LLM call via service | Network | Yes |
| `<node_name>` | Graph node | Yes |
| Response serialisation | CPU | Yes |

---

## Network / I/O Call Inventory

<!-- Count every external call per user request. -->

| Call | Service | Per-request count | In a loop? | Timeout set? |
|---|---|---|---|---|
| LLM invoke | `app/services/<name>.py` | 1 | No | [NOT VERIFIED] |
| KB retrieval | `app/services/<name>.py` | 0 / 1 / N | No / Yes | [NOT VERIFIED] |
| DynamoDB read | `app/services/<name>.py` | 0 / 1 / N | No / Yes | [NOT VERIFIED] |
| External HTTP | `app/services/<name>.py` | 0 / N | No / Yes | [NOT VERIFIED] |

**Total blocking external calls per request:** <!-- count -->

---

## Model Call Analysis

| Call | Node | Model | Prompt token estimate | Output token estimate | Justified? |
|---|---|---|---|---|---|
| | | | | | Yes / [PERFORMANCE RISK] |

**[PERFORMANCE RISK]** if > 1 model call per request without documented justification.

---

## Retrieval / Context Analysis

| Call | Source | Top-k | Max passage size | Total context injected | Bounded? |
|---|---|---|---|---|---|
| | | | | | Yes / [PERFORMANCE RISK] |

**[PERFORMANCE RISK]** if retrieved context size is unbounded or top-k is not set.

---

## Retry / Fallback Cost Analysis

<!-- Does any service have retry logic? How many retries per call? -->

| Service | Retry count | Backoff strategy | Max latency added |
|---|---|---|---|
| | 0 / N | None / Exponential | |

---

## Latency Risks

| Risk | Affected path | Label | Mitigation |
|---|---|---|---|
| Unbounded model call | Critical path | [PERFORMANCE RISK] | Set max tokens |
| Retrieval with no timeout | Critical path | [PERFORMANCE RISK] | Add timeout in service |
| Loop over external calls | | [PERFORMANCE RISK] | |

<!-- If no latency risks: write "None identified." -->

---

## Cost Risks

| Risk | Trigger | Label | Mitigation |
|---|---|---|---|
| Unbounded prompt tokens | User sends max-length message | [COST RISK] | Truncate context before injection |
| Multiple model calls per request | | [COST RISK] | |

<!-- If no cost risks at current scale: write "None at foundation stage." -->

---

## Scalability Risks

| Risk | Label | Deferred? |
|---|---|---|
| In-memory state between requests | [SCALE BLOCKER] | [DEFER] — single instance for now |
| Module-level singleton | [SCALE BLOCKER] | |

---

## Quota / Throttling Risks

| Service | Quota concern | Status |
|---|---|---|
| Bedrock model | Throttling on invocation limit | [NOT VERIFIED — no real calls yet] |
| DynamoDB | Read/write capacity | [NOT VERIFIED — not yet implemented] |

---

## Caching / Optimization Suggestions

<!-- Only suggest a cache if there is measured evidence of need. -->

| Suggestion | Justification | Label |
|---|---|---|
| | | [DEFER] if premature |

<!-- If no suggestions: write "No optimisations justified at current scale." -->

---

## Observability Requirements

<!-- What must be in place to detect performance regressions? -->

| Signal | Implementation | Status |
|---|---|---|
| Per-node latency logging | `logger.debug` at node entry/exit | [NOT VERIFIED — not yet implemented] |
| Model call latency | Logged in service | [NOT VERIFIED — service not yet built] |
| Token count per request | Logged by model service | [NOT VERIFIED] |

---

## Final Decision Reason

<!-- Write 1–3 sentences justifying the recommendation.
     Cite specific call counts and risks — do not say "looks fine." -->

> ...
