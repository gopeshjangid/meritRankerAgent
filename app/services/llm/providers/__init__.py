# app/services/llm_providers/__init__.py
# Package marker — provider implementations live in sibling modules.
#
# Part 6 public exports:
#   ProviderAdapter              — Protocol (base.py)
#   sanitize_provider_metadata   — helper (base.py)
#   LlmProviderAdapterError      — base adapter error (errors.py)
#   LlmProviderConfigurationError
#   LlmProviderExecutionError
#   LlmProviderResponseError
#   LlmProviderUnsupportedFeatureError
#   MockProviderAdapter          — mock adapter (mock_provider.py)
#   OpenAIProviderAdapter        — OpenAI adapter (openai_provider.py)
#   AzureOpenAIProviderAdapter   — Azure adapter (azure_openai_provider.py)
#   ProviderAdapterFactory       — factory (provider_factory.py)
