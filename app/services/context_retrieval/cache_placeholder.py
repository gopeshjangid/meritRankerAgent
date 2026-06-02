"""
app/services/context_retrieval/cache_placeholder.py
---------------------------------------------------
Future cache boundary — not wired in Part 13.1.

Part 13.1 intentionally has no active cache get/set path in
ContextRetrievalService. When caching is added, a wrapper or decorator
should sit before heavy Bedrock retrieval without changing graph nodes.

Planned direction (deferred):
  - Key inputs: normalised query hash, subject, intent, difficulty,
    exam/topic, retrieval_version — never raw query text in keys.
  - Value: ContextRetrievalResult only (not raw AWS responses).
  - Backends: Redis/ElastiCache or in-memory for local dev.
  - Graph continues to call ContextRetrievalService.retrieve_context() only.
"""
