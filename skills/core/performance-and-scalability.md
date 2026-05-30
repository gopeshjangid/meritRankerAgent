# Performance and Scalability — MeritRanker Tutor

> Rules for keeping the system fast, cost-efficient, and ready to scale.
> Do not optimise prematurely. Do not ignore real risks. Know the difference.

---

## The Core Rule

> **Understand the cost profile of every user-facing request before release.**
> You do not need to optimise it — but you must know what it does.

---

## Count What Matters on the User-Facing Path

For every feature, count:

- Number of model calls (LLM invocations) per user request.
- Number of retrieval calls (Knowledge Base, DynamoDB) per user request.
- Number of external HTTP calls per user request.
- Whether any of these are serialised (one after another) or parallelisable.

Document this in `skills/features/<feature>.md` under a `## Performance Notes` or
`## Known Limitations` section.

---

## Rules

### Model Calls

- Do not call an LLM more than necessary per user request.
- A verifier or re-ranking model call is only justified if the quality gain is proven.
  Add `[PERFORMANCE RISK]` annotation if adding extra model calls.
- Do not call a model inside a loop over user-supplied or retrieved items unless the
  loop is bounded and the bound is documented. [PERFORMANCE RISK]
- Model prompt and context must be bounded. Unbounded context = unbounded cost and
  unbounded latency. [PERFORMANCE RISK]

### Retrieval

- Bound the number of retrieved passages per call (e.g., `top_k=5`).
- Do not retrieve more context than the model can use effectively.
- Retrieval calls on the hot path must have a timeout. [PERFORMANCE RISK]
- Do not retrieve the same content more than once per request — pass it through state.

### External HTTP Calls

- Never make remote calls inside a loop without bounding the loop. [PERFORMANCE RISK]
- Set timeouts on every external call.
- If a call is not on the user-facing critical path, consider moving it to a background
  step (future work — do not add async/queue infrastructure prematurely).

### Caching

- Do not add a cache before it is justified by a measured problem.
- When a cache is added, define: TTL, invalidation strategy, what happens on cache miss.
- `[PERFORMANCE RISK]` Caching model output risks stale or incorrect answers.
  Invalidation must be designed before implementation.
- Cache only data that is safe to cache (no PII without an encryption plan).

---

## Critical Path vs Background

Separate user-facing work from background work:

| Work | Belongs on critical path? |
|---|---|
| Input validation | Yes |
| Graph execution | Yes |
| Model call for answer | Yes |
| DynamoDB question fetch | Yes (if needed for answer) |
| Logging / audit | No — async or fire-and-forget when possible |
| Usage metrics | No — async or background |
| Cache pre-warming | No — background |

Do not add queues, background workers, or async infrastructure prematurely.
Note deferred items as `[DEFER]` in feature context and return when scale justifies it.

---

## Statelessness

- Keep services stateless where possible.
- Do not store per-request state in module-level variables or global dicts.
- In-memory state between requests will break horizontal scaling. [PERFORMANCE RISK]
- If session state is needed, it belongs in a service (DynamoDB, AgentCore memory resource).

---

## Latency Measurement

- No latency measurement infrastructure exists yet. [NOT VERIFIED — baseline not established]
- When adding a real LLM or DynamoDB service, add start/end timestamps in the service
  and log them at DEBUG level. This creates a future measurement baseline.
- Do not add full distributed tracing infrastructure prematurely.

---

## Cost Risk Labels

Use these labels in feature docs and reviews:

| Label | Meaning |
|---|---|
| `[PERFORMANCE RISK]` | Likely latency or throughput problem at scale |
| `[COST RISK]` | Likely to add non-trivial per-request cost at volume |
| `[SCALE BLOCKER]` | Design that prevents horizontal scaling |
| `[DEFER]` | Real concern, optimisation not needed at current scale |

---

## What Not to Do

| Anti-pattern | Why |
|---|---|
| Add Redis before measuring cache hit rate | Premature infrastructure |
| Add SQS queue before measuring queue need | Premature infrastructure |
| Retrieve 50 KB of context per call | Unbounded cost and latency |
| Call an LLM twice to verify a non-critical answer | Unjustified double cost |
| Store all graph state in a module-level singleton | Breaks horizontal scaling |
| Ignore token limits because "it probably won't hit them" | Always document the limit |
