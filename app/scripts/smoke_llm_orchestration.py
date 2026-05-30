#!/usr/bin/env python3
"""
app/scripts/smoke_llm_orchestration.py
----------------------------------------
Manual-only smoke test for the LLM orchestration real-provider execution path.

NOT run by ``make check``, ``make test``, or normal pytest collection.
This script is an explicit opt-in tool for verifying that a real provider
adapter can reach an external API when given valid credentials.

Safety gate:
    The ``RUN_REAL_LLM_SMOKE`` environment variable MUST be set to the exact
    string ``"true"`` before this script makes any credential reads, SDK
    imports, or network calls.  If the variable is absent or has any other
    value the script prints an explanatory message and exits with code 0 — no
    credentials are read, no SDKs are imported.

Usage:
    # OpenAI
    RUN_REAL_LLM_SMOKE=true \\
      OPENAI_API_KEY=sk-... \\
      uv run python scripts/smoke_llm_orchestration.py \\
        --provider openai \\
        --query "Explain percentage increase in one sentence."

    # Azure OpenAI
    RUN_REAL_LLM_SMOKE=true \\
      AZURE_OPENAI_API_KEY=... \\
      AZURE_OPENAI_ENDPOINT=https://... \\
      AZURE_OPENAI_API_VERSION=2024-02-01 \\
      uv run python scripts/smoke_llm_orchestration.py \\
        --provider azure_openai \\
        --deployment my-gpt4o-deployment \\
        --query "Explain percentage increase in one sentence."

What this smoke tests:
    - Real provider adapter (OpenAI or Azure) can accept a ProviderExecutionRequest.
    - ProviderCredentialResolver correctly reads the required env vars.
    - Adapter returns a non-empty ModelExecutionResult.
    - Safe metadata (no API keys, no prompt, no messages) is printed.

What this does NOT test:
    - LlmOrchestrator (covered by dry-run and unit tests).
    - Mock provider (covered by test suite).
    - Graph wiring (deferred).
    - Streaming (deferred).

Exit codes:
    0 — Flag not set (no-op); or smoke completed successfully.
    1 — Smoke failed (provider error, missing credentials, arg error).
    2 — Unsupported --provider value.
"""

from __future__ import annotations

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Supported providers
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS: tuple[str, ...] = ("openai", "azure_openai")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # ------------------------------------------------------------------
    # SAFETY GATE: check flag BEFORE reading any credentials or importing
    # any provider/secret modules.
    # ------------------------------------------------------------------
    if os.environ.get("RUN_REAL_LLM_SMOKE", "").strip().lower() != "true":
        print(
            "RUN_REAL_LLM_SMOKE is not set to 'true'. "
            "Exiting without running real provider smoke."
        )
        print(
            "To run: "
            "RUN_REAL_LLM_SMOKE=true "
            "uv run python scripts/smoke_llm_orchestration.py "
            "--provider <openai|azure_openai> "
            "[--query '...'] "
            "[--deployment <azure-deployment>]"
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # Parse arguments (after flag check — no credential reads yet)
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Manual LLM orchestration real-provider smoke test.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=SUPPORTED_PROVIDERS,
        help="Provider to smoke-test: openai or azure_openai.",
    )
    parser.add_argument(
        "--query",
        default="Explain percentage increase in one sentence.",
        help="Query to send to the provider (kept short to minimise cost).",
    )
    parser.add_argument(
        "--deployment",
        default=None,
        help="Azure deployment name (required for --provider azure_openai).",
    )
    parser.add_argument(
        "--model-id",
        default="gpt-4o-mini",
        dest="model_id",
        help="OpenAI model_id (default: gpt-4o-mini). Ignored for azure_openai.",
    )
    args = parser.parse_args()

    if args.provider == "azure_openai" and not args.deployment:
        parser.error("--deployment is required when --provider is azure_openai")

    # ------------------------------------------------------------------
    # Provider-specific imports ONLY after the safety gate and arg checks.
    # ------------------------------------------------------------------
    # These imports are deferred so that the module-level flag check at the
    # top of main() is guaranteed to run before ANY credential/SDK module is
    # touched.  This makes smoke_guard tests simple and reliable.
    # ------------------------------------------------------------------
    from schemas.llm import LlmMessage  # noqa: PLC0415
    from schemas.llm_orchestration import (  # noqa: PLC0415
        ProviderExecutionRequest,
        ResolvedModelConfig,
    )
    from schemas.llm_routing import ModelConfig, ProviderProfile, RouteDecision  # noqa: PLC0415
    from services.llm_orchestration.model_execution import ProviderAdapterExecutor  # noqa: PLC0415
    from services.llm_providers.provider_factory import ProviderAdapterFactory  # noqa: PLC0415
    from services.secrets.env_secret_resolver import EnvSecretResolver  # noqa: PLC0415
    from services.secrets.provider_credentials import ProviderCredentialResolver  # noqa: PLC0415

    # ------------------------------------------------------------------
    # Build model config and provider profile for the chosen provider.
    # These are synthetic (not from production YAML) so we can exercise any
    # provider without modifying llm_orchestration.yaml.
    # ------------------------------------------------------------------
    if args.provider == "openai":
        model_cfg = ModelConfig(
            provider="openai",
            provider_profile="openai_primary",
            model_id=args.model_id,
            model_label=f"smoke-openai-{args.model_id}",
            cost_tier="low",
            supports_streaming=False,
            supports_thinking=False,
            timeout_seconds=30,
        )
        provider_profile = ProviderProfile(
            provider="openai",
            api_key_env="OPENAI_API_KEY",
        )
        profile_name = "openai_primary"
    else:  # azure_openai
        model_cfg = ModelConfig(
            provider="azure_openai",
            provider_profile="azure_primary",
            deployment=args.deployment,
            model_label=f"smoke-azure-{args.deployment}",
            cost_tier="low",
            supports_streaming=False,
            supports_thinking=False,
            timeout_seconds=30,
        )
        provider_profile = ProviderProfile(
            provider="azure_openai",
            api_key_env="AZURE_OPENAI_API_KEY",
            endpoint_env="AZURE_OPENAI_ENDPOINT",
            api_version_env="AZURE_OPENAI_API_VERSION",
        )
        profile_name = "azure_primary"

    resolved_config = ResolvedModelConfig(
        model_alias="smoke_model",
        model_config=model_cfg,  # uses Field alias
        provider_profile_name=profile_name,
        provider_profile=provider_profile,
        provider=args.provider,
        supports_streaming=False,
        supports_thinking=False,
        timeout_seconds=model_cfg.timeout_seconds,
    )

    # Synthetic RouteDecision — never from production YAML routes.
    route_decision = RouteDecision(
        route_id="smoke.generator.real",
        subject="general",
        task_role="generator",
        difficulty="default",
        model="smoke_model",
        prompt="subjects/general_generator.md",
        overlays=[],
        temperature=0.3,
        max_tokens=200,  # keep low to minimise cost
        provider_options={},
        fallback_attempts=[],
        route_source="safe_mock",  # marks this as a synthetic/forced route
    )

    # Simple user message for the smoke test.
    messages: list[LlmMessage] = [
        LlmMessage(role="user", content=args.query),
    ]

    request = ProviderExecutionRequest(
        route_decision=route_decision,
        model_resolution=resolved_config,
        messages=messages,
        temperature=route_decision.temperature,
        max_tokens=route_decision.max_tokens,
        provider_options={},
    )

    # ------------------------------------------------------------------
    # Build the execution stack and run.
    # ------------------------------------------------------------------
    credential_resolver = ProviderCredentialResolver(
        secret_resolver=EnvSecretResolver(),
    )
    provider_factory = ProviderAdapterFactory()  # default map with real adapters
    adapter_executor = ProviderAdapterExecutor(
        credential_resolver=credential_resolver,
        provider_factory=provider_factory,
    )

    print(f">>> Running real provider smoke: provider={args.provider!r}")
    print(f">>> Query: {args.query!r}")

    try:
        result = adapter_executor.execute(request)
    except Exception as exc:
        print(f"SMOKE FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Print ONLY safe metadata — never print api_key, prompt, or messages.
    # ------------------------------------------------------------------
    print("SMOKE PASSED")
    print(f"  model:          {result.model!r}")
    print(f"  provider:       {result.provider!r}")
    print(f"  finish_reason:  {result.finish_reason!r}")
    print(f"  input_tokens:   {result.input_tokens}")
    print(f"  output_tokens:  {result.output_tokens}")
    print(f"  latency_ms:     {result.latency_ms}")
    print(f"  content_len:    {len(result.content)} chars")
    sys.exit(0)


if __name__ == "__main__":
    main()
