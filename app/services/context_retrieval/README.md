# Context Retrieval (planned)

Placeholder package for the next Context Retrieval / RAG phase.

## Scope (future)

- Assemble `context_text` for the orchestrated doubt solver from approved sources.
- Keep retrieval logic out of graph nodes and out of LLM orchestration.

## Boundaries

| Layer | Responsibility |
|---|---|
| `graphs/doubt_solver_graph.py` | Orchestration only — calls services, no retrieval logic |
| `services/context_retrieval/` | Fetch, rank, truncate, and format context (future) |
| `services/llm/orchestration/` | Model routing, prompts, provider execution |
| `services/doubt_solver/` | Classifier adapter, answer generation, streaming |

## Not in scope yet

- Bedrock KB wiring
- DynamoDB record fetch
- Cache
- Planner / verifier / memory / web tools

Existing retrieval-related services at the repo root (`bedrock_kb_service`,
`question_record_service`, `context_builder_service`) remain on the legacy graph
path until migrated here.
