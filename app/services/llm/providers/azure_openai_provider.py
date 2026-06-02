"""
app/services/llm_providers/azure_openai_provider.py
------------------------------------------------------
Azure OpenAI provider implementations.

Legacy class (model_router / BaseLlmProvider path):
    AzureOpenAIProvider — reads credentials from os.environ at call time.

Part 6 adapter class (ProviderAdapterExecutor path):
    AzureOpenAIProviderAdapter — receives ProviderCredentials explicitly; supports
                                 injected fake client for unit testing.

Azure API modes (set via ProviderProfile.azure_api_mode):

    azure_deployment_chat_completions (default):
        Classic Azure OpenAI deployment endpoint.
        Uses AzureOpenAI(azure_endpoint=...) + deployment path.
        endpoint must be https://<resource>.openai.azure.com
        (must NOT end with /openai/v1).
        api_version required.

    azure_openai_v1:
        OpenAI-compatible /openai/v1 base URL.
        Uses OpenAI(base_url=...) — no deployment path appended.
        base_url (from endpoint or base_url credential) must end with /openai/v1
        or /openai/v1/.  Deployment passed as model= parameter.
        api_version NOT sent by our code (SDK handles base_url level).

Security rules:
- No API key, endpoint, or api_version may appear in logs, errors, or metadata.
- Error messages use only safe identifiers: model_alias, model_label, deployment,
  azure_api_mode.
- No env reads inside AzureOpenAIProviderAdapter.
- No SDK client created at import or construction time.

Important distinction:
- route_alias = request.route_decision.model  (route alias, not provider concept)
- deployment   = model_config.deployment      (Azure deployment name)
- model_label  = model_config.model_label     (human-readable label)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

from openai import AzureOpenAI

from schemas.llm import LlmRequest, LlmResponse, LlmRoleConfig, LlmStreamChunk
from services.llm.providers.base import BaseLlmProvider
from services.llm.providers.errors import (
    LlmConfigurationError,
    LlmGenerationError,
    LlmProviderConfigurationError,
    LlmProviderError,
    LlmProviderExecutionError,
    LlmProviderResponseError,
)

if TYPE_CHECKING:
    from schemas.llm_orchestration import ModelExecutionResult, ProviderExecutionRequest
    from services.secrets.provider_credentials import ProviderCredentials

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoint shape constants
# ---------------------------------------------------------------------------

_V1_SUFFIX = "/openai/v1"
_PROJECTS_SEGMENT = "/api/projects/"


def _normalize_v1_base_url(url: str) -> str:
    """Ensure base_url ends with exactly '/openai/v1/' for the OpenAI SDK.

    The OpenAI SDK requires base_url to end with '/'.
    Accepts trailing slash variants; does not rewrite the host.

    Raises ValueError if the URL does not contain '/openai/v1'.
    """
    stripped = url.rstrip("/")
    if not stripped.endswith(_V1_SUFFIX):
        raise ValueError(
            "azure_openai_v1 base_url must end with '/openai/v1' but got a URL "
            "without that suffix.  Correct example: "
            "https://<resource>.openai.azure.com/openai/v1"
        )
    return stripped + "/"


class AzureOpenAIProvider(BaseLlmProvider):
    """Azure OpenAI provider — reads credentials from environment at call time."""

    def _build_client(self, config: LlmRoleConfig) -> AzureOpenAI:
        """Construct and return an AzureOpenAI client.

        Credentials are read fresh from environment on every call so that
        runtime credential rotation is supported without restarting the process.

        Raises:
            LlmConfigurationError: If any required env var or config field is missing.
        """
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "")

        if not endpoint:
            raise LlmConfigurationError("AZURE_OPENAI_ENDPOINT is not set")
        if not api_key:
            raise LlmConfigurationError("AZURE_OPENAI_API_KEY is not set")
        if not api_version:
            raise LlmConfigurationError("AZURE_OPENAI_API_VERSION is not set")
        if not config.deployment:
            raise LlmConfigurationError(
                f"LlmRoleConfig.deployment is required for azure_openai "
                f"(model_label={config.model_label!r})"
            )

        # api_key is intentionally not logged
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    def generate(self, request: LlmRequest, config: LlmRoleConfig) -> LlmResponse:
        client = self._build_client(config)
        temperature = request.temperature if request.temperature is not None else config.temperature
        max_tokens = request.max_tokens if request.max_tokens is not None else config.max_tokens
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        logger.info(
            "azure_openai_provider.generate  role=%s  model_label=%s — start",
            request.role,
            config.model_label,
        )
        try:
            completion = client.chat.completions.create(
                model=config.deployment,  # deployment name, not model ID
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise LlmGenerationError(f"Azure OpenAI generation failed: {exc}") from exc

        content = completion.choices[0].message.content or ""
        finish_reason = completion.choices[0].finish_reason
        logger.info(
            "azure_openai_provider.generate  role=%s  model_label=%s — done",
            request.role,
            config.model_label,
        )
        return LlmResponse(
            role=request.role,
            provider="azure_openai",
            model_label=config.model_label,
            content=content,
            finish_reason=finish_reason,
        )

    def stream(self, request: LlmRequest, config: LlmRoleConfig) -> Iterator[LlmStreamChunk]:
        if not config.supports_streaming:
            raise LlmProviderError(
                f"Streaming is not enabled for model_label={config.model_label!r}. "
                "Set supports_streaming=true in the role config to enable it."
            )

        client = self._build_client(config)
        temperature = request.temperature if request.temperature is not None else config.temperature
        max_tokens = request.max_tokens if request.max_tokens is not None else config.max_tokens
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        logger.info(
            "azure_openai_provider.stream  role=%s  model_label=%s — start",
            request.role,
            config.model_label,
        )
        try:
            stream = client.chat.completions.create(
                model=config.deployment,  # deployment name, not model ID
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                finish_reason = chunk.choices[0].finish_reason
                is_final = finish_reason is not None
                yield LlmStreamChunk(
                    role=request.role,
                    provider="azure_openai",
                    model_label=config.model_label,
                    content_delta=delta,
                    is_final=is_final,
                )
        except LlmProviderError:
            raise
        except Exception as exc:
            raise LlmGenerationError(f"Azure OpenAI streaming failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Part 6 adapter — ProviderAdapterExecutor path
# ---------------------------------------------------------------------------


class AzureOpenAIProviderAdapter:
    """Part 6 Azure OpenAI provider adapter conforming to the ProviderAdapter protocol.

    Receives ProviderCredentials explicitly — does not read os.environ.
    Supports an injected ``client_factory`` for unit testing with fake clients.

    No SDK client is created at import or construction time.

    Two Azure API modes are supported (controlled by ``credentials.azure_api_mode``):

    azure_deployment_chat_completions (default):
        Uses AzureOpenAI(azure_endpoint=...) with the classic deployment path.
        ``credentials.endpoint`` must be https://<resource>.openai.azure.com
        (must NOT end with /openai/v1).
        ``credentials.api_version`` required.

    azure_openai_v1:
        Uses OpenAI(base_url=...) with the OpenAI-compatible /openai/v1 base URL.
        ``credentials.endpoint`` must end with /openai/v1 (or /openai/v1/).
        ``credentials.api_version`` is NOT required (not sent in URL path).
        Deployment is passed as model= parameter only.

    Credential rules:
    - ``credentials.api_key`` is required in both modes.
    - Credential values must never appear in logs, errors, or metadata.

    Model selection:
    - Uses ``request.model_resolution.model_config.deployment`` as the Azure
      deployment name.  This is not the route alias and not model_id.
    """

    def __init__(
        self,
        *,
        client_factory: Callable[[ProviderCredentials], Any] | None = None,
    ) -> None:
        """
        Args:
            client_factory: Optional callable(credentials) -> client.
                Used to inject a fake client in unit tests.
                When None, a real SDK client is created at call time based on
                azure_api_mode (AzureOpenAI or OpenAI).
        """
        self._client_factory = client_factory
        self.last_stream_finish_reason: str | None = None

    # ------------------------------------------------------------------
    # Client builders — one per Azure API mode
    # ------------------------------------------------------------------

    def _build_client_classic(self, credentials: ProviderCredentials) -> Any:
        """Build an AzureOpenAI client for azure_deployment_chat_completions mode.

        Uses AzureOpenAI(azure_endpoint=..., api_version=..., api_key=...).
        The SDK appends /openai/deployments/<deployment>/chat/completions?api-version=...
        to the endpoint automatically.

        Preconditions (validated before calling):
        - credentials.endpoint does NOT end with /openai/v1
        - credentials.api_version is set
        """
        if self._client_factory is not None:
            return self._client_factory(credentials)
        from openai import AzureOpenAI as _AzureOpenAI  # noqa: PLC0415

        return _AzureOpenAI(
            api_key=credentials.api_key,
            azure_endpoint=credentials.endpoint,
            api_version=credentials.api_version,
            max_retries=0,
        )

    def _build_client_v1(self, credentials: ProviderCredentials) -> Any:
        """Build an OpenAI client for azure_openai_v1 mode.

        Uses OpenAI(base_url=<normalised /openai/v1/>, api_key=...).
        The SDK appends /chat/completions to base_url — no deployment path.

        Preconditions (validated before calling):
        - credentials.endpoint ends with /openai/v1 (or /openai/v1/)
        """
        if self._client_factory is not None:
            return self._client_factory(credentials)
        from openai import OpenAI as _OpenAI  # noqa: PLC0415

        base_url = _normalize_v1_base_url(credentials.endpoint or "")
        return _OpenAI(
            api_key=credentials.api_key,
            base_url=base_url,
            max_retries=0,
        )

    # ------------------------------------------------------------------
    # generate — validation + dispatch
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        request: ProviderExecutionRequest,
        credentials: ProviderCredentials,
    ) -> ModelExecutionResult:
        """Execute the request against Azure OpenAI and return a normalized result.

        Dispatches to the correct Azure API mode based on
        ``credentials.azure_api_mode``.

        Args:
            request:     The resolved provider execution request.
            credentials: Resolved Azure OpenAI credentials.

        Returns:
            ModelExecutionResult with provider="azure_openai".

        Raises:
            LlmProviderConfigurationError: Missing credentials, deployment, or
                                           endpoint/mode mismatch.
            LlmProviderExecutionError:     SDK call failed.
            LlmProviderResponseError:      Response content is empty/missing.
        """
        from schemas.llm_orchestration import ModelExecutionResult  # noqa: PLC0415

        if not credentials.api_key:
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter requires credentials.api_key."
            )

        azure_api_mode = credentials.azure_api_mode or "azure_deployment_chat_completions"

        if azure_api_mode == "azure_openai_v1":
            client = self._validate_and_build_v1(credentials)
        else:
            client = self._validate_and_build_classic(credentials)

        deployment = request.model_resolution.model_config.deployment
        if not deployment:
            raise LlmProviderConfigurationError(
                f"deployment is required for the Azure OpenAI provider adapter "
                f"(model_alias={request.model_resolution.model_alias!r}, "
                f"azure_api_mode={azure_api_mode!r})."
            )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        logger.info(
            "azure_openai_provider_adapter.generate  model_alias=%s  deployment=%s"
            "  azure_api_mode=%s — start",
            request.model_resolution.model_alias,
            deployment,
            azure_api_mode,
        )

        try:
            completion = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as exc:
            failure_kind = _classify_azure_openai_error(exc)
            raise LlmProviderExecutionError(
                f"Azure OpenAI call failed for"
                f" model_alias={request.model_resolution.model_alias!r},"
                f" azure_api_mode={azure_api_mode!r}:"
                f" {type(exc).__name__}",
                failure_kind=failure_kind,
                provider="azure_openai",
                model_alias=request.model_resolution.model_alias,
            ) from exc

        content = self._extract_content(completion, request)
        finish_reason = self._extract_finish_reason(completion)
        input_tokens, output_tokens = self._extract_usage(completion)

        logger.info(
            "azure_openai_provider_adapter.generate  model_alias=%s — done  "
            "finish_reason=%s  input_tokens=%s  output_tokens=%s",
            request.model_resolution.model_alias,
            finish_reason,
            input_tokens,
            output_tokens,
        )

        return ModelExecutionResult(
            content=content,
            model=request.route_decision.model,
            provider="azure_openai",
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={
                "model_label": request.model_resolution.model_config.model_label,
                "deployment": deployment,
                "azure_api_mode": azure_api_mode,
            },
        )

    def generate_stream(
        self,
        *,
        request: ProviderExecutionRequest,
        credentials: ProviderCredentials,
    ) -> Iterator[str]:
        """Stream text deltas from Azure OpenAI (OpenAI-compatible v1 or classic).

        Yields answer text chunks only — no prompt, messages, or provider metadata.
        """
        if not credentials.api_key:
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter requires credentials.api_key."
            )

        azure_api_mode = credentials.azure_api_mode or "azure_deployment_chat_completions"

        if azure_api_mode == "azure_openai_v1":
            client = self._validate_and_build_v1(credentials)
        else:
            client = self._validate_and_build_classic(credentials)

        deployment = request.model_resolution.model_config.deployment
        if not deployment:
            raise LlmProviderConfigurationError(
                f"deployment is required for the Azure OpenAI provider adapter "
                f"(model_alias={request.model_resolution.model_alias!r}, "
                f"azure_api_mode={azure_api_mode!r})."
            )

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        logger.info(
            "azure_openai_provider_adapter.generate_stream  model_alias=%s  deployment=%s"
            "  azure_api_mode=%s — start",
            request.model_resolution.model_alias,
            deployment,
            azure_api_mode,
        )

        try:
            stream = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            finish_reason: str | None = None
            for chunk in stream:
                if not chunk.choices:
                    continue
                fr = getattr(chunk.choices[0], "finish_reason", None)
                if fr is not None:
                    finish_reason = fr
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
            self.last_stream_finish_reason = finish_reason or "stop"
        except Exception as exc:
            failure_kind = _classify_azure_openai_error(exc)
            raise LlmProviderExecutionError(
                f"Azure OpenAI stream failed for"
                f" model_alias={request.model_resolution.model_alias!r},"
                f" azure_api_mode={azure_api_mode!r}:"
                f" {type(exc).__name__}",
                failure_kind=failure_kind,
                provider="azure_openai",
                model_alias=request.model_resolution.model_alias,
            ) from exc

    # ------------------------------------------------------------------
    # Mode-specific credential validation helpers
    # ------------------------------------------------------------------

    def _validate_and_build_classic(self, credentials: ProviderCredentials) -> Any:
        """Validate credentials for azure_deployment_chat_completions mode and build client.

        Raises:
            LlmProviderConfigurationError: If endpoint is missing, ends with
                /openai/v1, or api_version is missing.
        """
        if not credentials.endpoint:
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_deployment_chat_completions) "
                "requires credentials.endpoint "
                "(https://<resource>.openai.azure.com — must NOT end with /openai/v1)."
            )
        if _PROJECTS_SEGMENT in (credentials.endpoint or ""):
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_deployment_chat_completions): "
                "endpoint contains '/api/projects/' which is a Foundry project endpoint. "
                "Use azure_api_mode: azure_openai_v1 or a plain classic Azure OpenAI endpoint."
            )
        stripped = credentials.endpoint.rstrip("/")
        if stripped.endswith(_V1_SUFFIX):
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_deployment_chat_completions): "
                "endpoint ends with '/openai/v1' which is an OpenAI-compatible v1 base URL. "
                "Set azure_api_mode: azure_openai_v1 in provider_profiles.yaml to use "
                "this endpoint, or change endpoint to the plain Azure OpenAI resource URL "
                "(https://<resource>.openai.azure.com)."
            )
        if not credentials.api_version:
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_deployment_chat_completions) "
                "requires credentials.api_version."
            )
        return self._build_client_classic(credentials)

    def _validate_and_build_v1(self, credentials: ProviderCredentials) -> Any:
        """Validate credentials for azure_openai_v1 mode and build client.

        Raises:
            LlmProviderConfigurationError: If endpoint is missing or does not
                end with /openai/v1.
        """
        if not credentials.endpoint:
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_openai_v1) "
                "requires credentials.endpoint ending with /openai/v1 "
                "(e.g. https://<resource>.openai.azure.com/openai/v1)."
            )
        stripped = credentials.endpoint.rstrip("/")
        if not stripped.endswith(_V1_SUFFIX):
            raise LlmProviderConfigurationError(
                "AzureOpenAIProviderAdapter (azure_openai_v1): endpoint must end "
                "with '/openai/v1' but the configured endpoint does not. "
                "Expected https://<resource>.openai.azure.com/openai/v1"
            )
        return self._build_client_v1(credentials)

    @staticmethod
    def _extract_content(completion: Any, request: ProviderExecutionRequest) -> str:
        try:
            content = completion.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            content = None
        if not content:
            raise LlmProviderResponseError(
                f"Azure OpenAI response is missing content "
                f"(model_alias={request.model_resolution.model_alias!r})."
            )
        return content

    @staticmethod
    def _extract_finish_reason(completion: Any) -> str | None:
        try:
            return completion.choices[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            return None

    @staticmethod
    def _extract_usage(completion: Any) -> tuple[int | None, int | None]:
        try:
            return completion.usage.prompt_tokens, completion.usage.completion_tokens
        except AttributeError:
            return None, None


# ---------------------------------------------------------------------------
# Azure OpenAI error classifier (Part 9.1 — provider failure kind mapping)
# ---------------------------------------------------------------------------


def _is_deployment_or_model_config_error(exc: BaseException) -> bool:
    """Detect Azure/OpenAI errors caused by invalid or missing deployment/model."""
    body = str(getattr(exc, "body", "") or "").lower()
    message = str(exc).lower()
    combined = f"{body} {message}"
    markers = (
        "deployment",
        "model_not_found",
        "model not found",
        "does not exist",
        "invalid model",
        "unknown model",
        "model is not available",
        "no such model",
    )
    return any(marker in combined for marker in markers)


def _classify_azure_openai_error(exc: BaseException) -> str:
    """Map an openai SDK exception (Azure path) to a safe ProviderFailureKind string.

    Azure OpenAI uses the same openai SDK, so the exception hierarchy is
    identical.  Azure 429 errors may or may not carry an insufficient_quota code;
    most Azure quota errors surface as RateLimitError.

    Security: this function must NOT include API keys, endpoints, or raw
    response bodies in the returned string.
    """
    try:
        import openai as _openai  # noqa: PLC0415
    except ImportError:
        return "unknown_provider_error"

    if isinstance(exc, _openai.RateLimitError):
        error_code = getattr(exc, "code", None) or ""
        error_body = str(getattr(exc, "body", "") or "")
        if error_code == "insufficient_quota" or "insufficient_quota" in error_body:
            return "insufficient_quota"
        return "rate_limited"

    if isinstance(exc, (_openai.AuthenticationError, _openai.PermissionDeniedError)):
        return "authentication_failed"

    if isinstance(exc, _openai.NotFoundError):
        # Azure 404 can mean: deployment not found, resource not found.
        return "model_not_found"

    if isinstance(exc, _openai.APITimeoutError):
        return "timeout"

    if isinstance(exc, _openai.APIConnectionError):
        return "provider_unavailable"

    if isinstance(exc, _openai.BadRequestError):
        if _is_deployment_or_model_config_error(exc):
            return "model_not_found"
        return "invalid_request"

    if isinstance(exc, _openai.APIStatusError):
        status = getattr(exc, "status_code", 0) or 0
        if status in (401, 403):
            return "authentication_failed"
        if status == 429:
            return "rate_limited"
        if status == 404:
            return "model_not_found"
        if status == 400 and _is_deployment_or_model_config_error(exc):
            return "model_not_found"
        if status >= 500:
            return "provider_unavailable"

    return "unknown_provider_error"
