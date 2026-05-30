"""
app/services/query_classifier_service.py
-----------------------------------------
Query classifier service with deterministic fallback and optional LLM path.

Dispatch rules:
  ENABLE_REAL_LLM=false                              → deterministic
  ENABLE_REAL_LLM=true, role not in config           → deterministic
  ENABLE_REAL_LLM=true, role configured, call fails  → fallback (deterministic + low confidence)
  ENABLE_REAL_LLM=true, role configured, call OK     → llm

Public API:
    classify_query(query: str) -> QueryClassification
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from schemas.doubt_solver import QueryClassification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLASSIFIER_ROLE = "doubt_solver_classifier"

# ---------------------------------------------------------------------------
# Lazy orchestrator singleton — orchestrated path
# ---------------------------------------------------------------------------

# Initialised on first call to _get_classifier_orchestrator().
# Reset to None in tests that need a clean slate.
_classifier_orchestrator: object | None = None


def _get_classifier_orchestrator() -> object:
    """Build (or return cached) LlmOrchestrator for the orchestrated classifier path.

    Wires the same provider chain as main.py when ENABLE_REAL_LLM=true.
    Called only when ENABLE_ORCHESTRATED_DOUBT_SOLVER=true and ENABLE_REAL_LLM=true.
    """
    global _classifier_orchestrator  # noqa: PLW0603
    if _classifier_orchestrator is not None:
        return _classifier_orchestrator

    # Deferred heavy imports — only loaded when orchestrated path is active.
    from services.llm.orchestration.model_config_resolver import (  # noqa: PLC0415
        ModelConfigResolver,
    )
    from services.llm.orchestration.model_execution import (  # noqa: PLC0415
        ProviderAdapterExecutor,
        RegistryBackedModelExecutor,
    )
    from services.llm.orchestration.orchestrator import LlmOrchestrator  # noqa: PLC0415
    from services.llm.providers.provider_factory import (  # noqa: PLC0415
        ProviderAdapterFactory,
    )
    from services.secrets.env_secret_resolver import EnvSecretResolver  # noqa: PLC0415
    from services.secrets.provider_credentials import (  # noqa: PLC0415
        ProviderCredentialResolver,
    )

    _secret_resolver = EnvSecretResolver()
    _credential_resolver = ProviderCredentialResolver(secret_resolver=_secret_resolver)
    _adapter_executor = ProviderAdapterExecutor(
        credential_resolver=_credential_resolver,
        provider_factory=ProviderAdapterFactory(),
    )
    _model_executor = RegistryBackedModelExecutor(
        provider_executor=_adapter_executor,
        model_config_resolver=ModelConfigResolver(),
    )

    # Preflight: block orchestrator construction if any Azure deployment is a
    # placeholder.  Only reached when ENABLE_REAL_LLM=true (callers check first).
    # [SECURITY] Error includes only model alias names — no keys or secrets.
    from services.llm.orchestration.config_registry import get_registry  # noqa: PLC0415

    get_registry().validate_real_mode_deployments()  # raises LlmConfigValidationError

    _classifier_orchestrator = LlmOrchestrator(model_executor=_model_executor)
    return _classifier_orchestrator


# ---------------------------------------------------------------------------
# Keyword maps — deterministic path
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "solve_question": ["solve", "calculate", "find", "compute", "evaluate", "what is", "answer"],
    "explain_concept": [
        "explain",
        "concept",
        "why",
        "what does",
        "what are",
        "define",
        "describe",
        "meaning of",
    ],
    "explain_option": ["option", "choice", "correct", "why is option", "why option", "why answer"],
}

_SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "math": [
        "profit",
        "loss",
        "equation",
        "calculate",
        "compute",
        "percentage",
        "ratio",
        "fraction",
        "algebra",
        "geometry",
        "number",
        "sum",
        "product",
        "divide",
    ],
    "english": ["grammar", "vocabulary", "sentence", "word", "synonym", "antonym", "tense"],
    "reasoning": ["series", "pattern", "sequence", "analogy", "odd one out", "logical"],
    "science": ["physics", "chemistry", "biology", "force", "energy", "atom", "molecule"],
}

_DIFFICULTY_KEYWORDS: dict[str, list[str]] = {
    "advanced": [
        "advanced",
        "hard",
        "tough",
        "tricky",
        "high level",
        "ssc cgl level",
        "cat level",
        "upsc level",
    ],
    "basic": [
        "basic",
        "simple",
        "beginner",
        "easy",
    ],
    "intermediate": [
        "intermediate",
        "moderate",
    ],
}


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def _detect_intent(query_lower: str) -> tuple[str, float]:
    """Return (intent, confidence) from keyword matching."""
    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                return intent, 0.75
    return "general_doubt", 0.55


def _detect_subject(query_lower: str) -> str:
    """Return subject string from keyword matching."""
    for subject, keywords in _SUBJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                return subject
    return "unknown"


def _detect_style(query_lower: str, intent: str) -> str:
    """Return response_style from keyword matching, falling back to intent default."""
    if "short" in query_lower:
        return "short_answer"
    if "simple" in query_lower:
        return "simple_explanation"
    mapping = {
        "solve_question": "step_by_step",
        "explain_concept": "simple_explanation",
        "explain_option": "short_answer",
        "general_doubt": "simple_explanation",
        "unknown": "step_by_step",
    }
    return mapping.get(intent, "step_by_step")


def _detect_difficulty(query_lower: str) -> str:
    """Return difficulty from keyword matching. Returns 'default' when no signal."""
    for difficulty, keywords in _DIFFICULTY_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                return difficulty
    return "default"


def _classify_deterministic(query: str) -> QueryClassification:
    """Classify a student query using keyword matching. No network calls."""
    query_lower = query.lower()
    intent, confidence = _detect_intent(query_lower)
    subject = _detect_subject(query_lower)
    difficulty = _detect_difficulty(query_lower)
    response_style = _detect_style(query_lower, intent)

    result = QueryClassification(
        intent=intent,  # type: ignore[arg-type]
        subject=subject,
        topic=None,
        difficulty=difficulty,  # type: ignore[arg-type]
        response_style=response_style,  # type: ignore[arg-type]
        confidence=confidence,
        classification_source="deterministic",
    )
    logger.debug(
        "deterministic_classifier  intent=%s  subject=%s  difficulty=%s  confidence=%.2f",
        result.intent,
        result.subject,
        result.difficulty,
        result.confidence,
    )
    return result


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


def _load_classifier_prompt() -> str:
    """Return the classifier system prompt (cached after first read)."""
    from services.prompt_loader import load_prompt  # noqa: PLC0415

    return load_prompt("query_classifier")


def _classify_with_llm_orchestrated(
    query: str, request_id: str | None = None
) -> QueryClassification:
    """Run classification via the orchestrated Azure-first path.

    Resolves route with subject="general", task_role="classifier",
    difficulty="default" — hitting doubt_solver_classifier (Azure primary)
    with doubt_solver_classifier_openai_native as fallback.

    Args:
        query:      The student's question (already validated by caller).
        request_id: Trace ID propagated from the graph state.  If None
                    (legacy callers without a trace ID), a new UUID is
                    generated at this boundary so RouteRequest validation
                    does not fail.  Callers should always pass the
                    originating request_id when available.

    Raises:
        Any exception from orchestrator, JSON parsing, or validation.
        Caller must handle (ProviderExecutionError, JSONDecodeError, etc.).
    """
    from schemas.llm_routing import RouteRequest  # noqa: PLC0415

    # Use the provided request_id; generate one at the boundary only when the
    # caller has no trace ID (non-orchestrated legacy entrypoints).
    _request_id = request_id or str(uuid.uuid4())

    orchestrator = _get_classifier_orchestrator()
    route_request = RouteRequest(
        request_id=_request_id,
        subject="general",
        task_role="classifier",
        difficulty="default",
        intent="classify",
    )

    result = orchestrator.generate(  # type: ignore[union-attr]
        route_request=route_request,
        query=query,
        classification=None,
        context=None,
    )

    # [AI RISK] LLM output is untrusted — parse and validate before use.
    raw = json.loads(result.content)
    classification = QueryClassification.model_validate(raw)
    return QueryClassification(
        intent=classification.intent,
        subject=classification.subject,
        topic=classification.topic,
        difficulty=classification.difficulty,
        response_style=classification.response_style,
        confidence=classification.confidence,
        retrieval_need=classification.retrieval_need,
        reasoning_summary=classification.reasoning_summary,
        classification_source="llm",
    )


def _classify_with_llm_orchestrated_or_fallback(
    query: str, request_id: str | None = None
) -> QueryClassification:
    """Run orchestrated classifier; fall back to deterministic on any failure."""
    t_start = time.perf_counter()
    try:
        result = _classify_with_llm_orchestrated(query, request_id=request_id)
        duration_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "orchestrated_classifier  intent=%s  confidence=%.2f  source=llm  duration_ms=%.2f",
            result.intent,
            result.confidence,
            duration_ms,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Orchestrated classifier failed — falling back to deterministic: %s", exc
        )
        fallback = _classify_deterministic(query)
        return QueryClassification(
            intent=fallback.intent,
            subject=fallback.subject,
            topic=fallback.topic,
            difficulty=fallback.difficulty,
            response_style=fallback.response_style,
            confidence=min(fallback.confidence, 0.55),
            retrieval_need=fallback.retrieval_need,
            classification_source="fallback",
        )


def _classify_with_llm(query: str) -> QueryClassification:
    """Call model_router and parse the structured JSON response.

    Raises:
        Any exception from model_router or JSON parsing — caller must handle.
    """
    # Deferred imports: only loaded when LLM path is active.
    from schemas.llm import LlmMessage  # noqa: PLC0415
    from services import model_router  # noqa: PLC0415

    system_prompt = _load_classifier_prompt()
    messages = [
        LlmMessage(role="system", content=system_prompt),
        LlmMessage(role="user", content=query),
    ]

    response = model_router.generate(_CLASSIFIER_ROLE, messages)

    # [AI RISK] LLM output is untrusted — parse and validate before use.
    raw = json.loads(response.content)
    classification = QueryClassification.model_validate(raw)

    # Override source field regardless of what the model returned.
    return QueryClassification(
        intent=classification.intent,
        subject=classification.subject,
        topic=classification.topic,
        difficulty=classification.difficulty,
        response_style=classification.response_style,
        confidence=classification.confidence,
        retrieval_need=classification.retrieval_need,
        reasoning_summary=classification.reasoning_summary,
        classification_source="llm",
    )


def _classify_with_llm_or_fallback(query: str) -> QueryClassification:
    """Try LLM classification; fall back to deterministic on any failure."""
    t_start = time.perf_counter()
    try:
        result = _classify_with_llm(query)
        duration_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "llm_classifier  intent=%s  confidence=%.2f  source=llm  duration_ms=%.2f",
            result.intent,
            result.confidence,
            duration_ms,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        # Log safe warning — exc may contain partial model output; never log query.
        logger.warning("LLM classifier failed — falling back to deterministic: %s", exc)
        fallback = _classify_deterministic(query)
        return QueryClassification(
            intent=fallback.intent,
            subject=fallback.subject,
            topic=fallback.topic,
            difficulty=fallback.difficulty,
            response_style=fallback.response_style,
            confidence=min(fallback.confidence, 0.55),
            retrieval_need=fallback.retrieval_need,
            classification_source="fallback",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_query(query: str, request_id: str | None = None) -> QueryClassification:
    """Classify a student query, dispatching to LLM or deterministic based on config.

    Args:
        query:      The student's question or doubt (already validated by entrypoint).
        request_id: Trace ID from the originating request.  Pass
                    ``state["request_id"]`` from graph nodes.  Optional for
                    legacy callers — a new UUID is generated at the boundary
                    when not provided.

    Returns:
        A validated QueryClassification instance.
    """
    # Deferred import so dotenv has loaded before config is read.
    from config import get_settings  # noqa: PLC0415

    t_start = time.perf_counter()
    settings = get_settings()

    if not settings.enable_real_llm:
        result = _classify_deterministic(query)
        duration_ms = (time.perf_counter() - t_start) * 1000
        logger.debug(
            "classify_query  source=deterministic  intent=%s  duration_ms=%.2f",
            result.intent,
            duration_ms,
        )
        return result

    # Orchestrated path — Azure-first via model registry when
    # ENABLE_ORCHESTRATED_DOUBT_SOLVER=true.
    if settings.enable_orchestrated_doubt_solver:
        return _classify_with_llm_orchestrated_or_fallback(query, request_id=request_id)

    # Legacy model_router path — ENABLE_ORCHESTRATED_DOUBT_SOLVER=false.
    # Check whether the classifier role is explicitly configured.
    # If ENABLE_REAL_LLM=true but the role is missing, fall back gracefully
    # rather than raising a hard error — classification is non-critical.
    try:
        role_map: dict = json.loads(settings.llm_role_config_json)
    except Exception:  # noqa: BLE001
        # [SECURITY] Do not log the raw config value — it may contain partial keys.
        logger.warning(
            "classify_query: LLM_ROLE_CONFIG_JSON is not valid JSON — "
            "ENABLE_REAL_LLM=true but config cannot be parsed; returning fallback classification"
        )
        _det = _classify_deterministic(query)
        return QueryClassification(
            intent=_det.intent,
            subject=_det.subject,
            topic=_det.topic,
            difficulty=_det.difficulty,
            response_style=_det.response_style,
            confidence=min(_det.confidence, 0.55),
            retrieval_need=_det.retrieval_need,
            classification_source="fallback",
        )

    if _CLASSIFIER_ROLE not in role_map:
        logger.debug(
            "classify_query: role %r not in LLM_ROLE_CONFIG_JSON — using deterministic",
            _CLASSIFIER_ROLE,
        )
        return _classify_deterministic(query)

    return _classify_with_llm_or_fallback(query)
