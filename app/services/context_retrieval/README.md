# Context Retrieval (Part 13.1 + RAG correctness fix)

Production context retrieval foundation for the orchestrated doubt solver.

## Graph-facing API

Only `ContextRetrievalService.retrieve_context()` is called from graph nodes.
The graph receives `context_text` only — no KB metadata or AWS shapes.

```
student query
→ classifier (+ strong classifier if confidence < configured threshold, default 0.92)
→ apply_classification_policy (deterministic difficulty correction)
→ collect_context
→ ContextRetrievalService
→ retrieval decision (policy-protected)
→ Bedrock KB retrieve lanes (if needed)
→ deterministic rerank (top 1–2, confidence >= 0.85)
→ compact context_text
→ generator
```

## KB metadata filtering

Each KB chunk is one approved Pattern (`pattern-sandbox/chunks/{patternId}.txt`).

### Subject mapping (app → KB metadata)

| App subject | KB metadata `subject` |
|---|---|
| math, quantitative, quant | QUANT |
| reasoning | REASONING |
| english | ENGLISH |
| general, gk | GK |
| unknown | no subject filter (broad lane) |

### Strict filter fields (this phase)

- `subject` (mapped KB value)
- `patternTopicKey`
- `patternFamilyKey`
- `schemaVersion` (`"v2"` when configured)
- `taxonomyReviewRequired` (`"false"` when production-safe)

All filter values are **strings** (e.g. `"false"`, not boolean `false`).

### Intentionally avoided as strict prefilters

- `complexityLevel` (soft rerank signal only)
- `confidence` (soft rerank signal only)
- `level`, `conceptTags`, raw `topic`, app `difficulty`

## Pattern hint extraction

`derive_pattern_hints(query, subject, classification)` maps query keywords to canonical
`patternTopicKey` values (e.g. coded inequality → `CODED_INEQUALITY`, profit/loss →
`PROFIT_LOSS_DISCOUNT`). Hints drive SUBJECT_TOPIC / SUBJECT_TOPIC_FAMILY lanes and rerank
topic_match bonus. Weak signals leave `pattern_topic_key` empty (subject-only fallback).

## Rerank diagnostics

Top 3 candidates log safe breakdown fields (`context_rerank_breakdown`): bedrock_score,
subject/topic/family match flags, keyword/concept overlap scores, approved_signal, risk,
rejection_reason. When top confidence is 0.70–0.85, logs include `near_miss=true` but
context is **not** passed to the generator (threshold remains 0.85).

## Summary logs

- `context_retrieval_summary` — lane, aws/normalized/selected counts, reason, context_chars
- `context_rerank_summary` — candidate/selected counts, top_confidence, near_miss
- `classification_policy_summary` — subject, difficulty, pattern_topic, matched_signal

## Retrieval lanes (max 5)

1. **SUBJECT_TOPIC_FAMILY** — subject + patternTopicKey + patternFamilyKey + production filters
2. **SUBJECT_TOPIC** — subject + patternTopicKey + production filters
3. **SUBJECT_ONLY** — subject + production filters
4. **RELAXED_SUBJECT_ONLY** — subject only; no schemaVersion; no taxonomyReviewRequired
5. **BROAD_SEMANTIC** — no subject/topic/family; no taxonomy filter; schemaVersion only if mandatory

Strict lanes run first, then same-subject relaxed search, then broad semantic as last resort.

Production filters (`schemaVersion`, `taxonomyReviewRequired`) apply to lanes 1–3 only.

## Missing metadata handling

Incomplete KB metadata is treated as **risk + score penalty**, not automatic rejection:

- missing `subject`, `patternId`, `patternTopicKey`, `confidence`, `taxonomyReviewRequired` → downrank
- explicit subject/topic/family **mismatch** → hard reject
- `taxonomyReviewRequired="true"` → hard reject on strict lanes; downrank on relaxed lanes

## Outcome reasons

| Result `reason` | Meaning |
|---|---|
| `no_kb_candidates` | All lanes returned AWS count 0 |
| `normalization_dropped_all_candidates` | AWS returned records but none normalized |
| `no_high_confidence_context` | Normalized items exist but none reached rerank confidence >= 0.85 |
| `context_selected` | High-confidence context selected for generator |

**Note:** `BEDROCK_KB_MIN_SCORE` is not used as a pre-normalization hard filter.
Bedrock score is preserved for deterministic reranking only.

## Deterministic reranking

No LLM/model reranker in this phase (`ENABLE_CONTEXT_MODEL_RERANKER` deferred).

Scoring uses Bedrock score + metadata/body signals. Hard reject only for empty text,
explicit metadata mismatch, or `taxonomyReviewRequired="true"` on strict lanes.

**Final selection:** top 2 candidates where `rerank_confidence >= 0.85`.
Below threshold → `context_text=""`, `reason=no_high_confidence_context`.

Exact Pattern linking by vector score alone is **not** performed — verify before relying.

## Classification policy correction

After LLM classification, `apply_classification_policy()` corrects difficulty
and subject when explicit signals appear in the query (e.g. SBI PO, profit/loss,
coded inequality, grammar). High classifier confidence does not block correction.
Applies to both streaming and non-streaming orchestrated paths.

## Cache (deferred)

No active `cache.get` / `cache.set` path. See `cache_placeholder.py`.

## Config env vars

| Variable | Default |
|---|---|
| `ENABLE_KB_RETRIEVAL` | `false` |
| `CONTEXT_KB_SCHEMA_VERSION` | `v2` (empty disables filter) |
| `CONTEXT_KB_SCHEMA_VERSION_MANDATORY` | `false` (when true, BROAD lane keeps schemaVersion) |
| `CONTEXT_KB_TAXONOMY_APPROVED_ONLY` | `true` |
| `CONTEXT_MAX_CHARS` | `2500` |
| `CONTEXT_KB_TOP_K` | `5` |
| `CONTEXT_RERANK_TOP_N` | `2` |

## Deferred

- Model/LLM reranker (`ENABLE_CONTEXT_MODEL_RERANKER`)
- Exact pattern verifier / semantic matcher
- Active cache (Redis/ElastiCache)
- DynamoDB indexed retrieval
- Web search
- Planner / validator / memory
