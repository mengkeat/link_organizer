"""
LLM Provider Factory
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
from .base import LLMProvider
from .litellm_provider import LiteLLMProvider
from .openrouter_provider import OpenRouterProvider


class LLMProviderType(Enum):
    """Available LLM provider types"""
    LITELLM = "litellm"
    OPENROUTER = "openrouter"


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    PROVIDERS = {
        LLMProviderType.LITELLM: LiteLLMProvider,
        LLMProviderType.OPENROUTER: OpenRouterProvider,
    }

    @classmethod
    def create_provider(
        cls,
        provider_type: LLMProviderType,
        api_key: str,
        model: str,
        **kwargs
    ) -> LLMProvider:
        """Create an LLM provider instance"""
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(api_key=api_key, model=model, **kwargs)

    @classmethod
    def from_env(
        cls,
        provider_env_var: str = "LLM_PROVIDER",
        api_key_env_var: str = "OPENROUTER_API_KEY",
        model_env_var: str = "LITELLM_MODEL",
        default_provider: LLMProviderType = LLMProviderType.LITELLM
    ) -> LLMProvider:
        """Create provider from environment variables"""
        # Get provider type from environment
        provider_str = os.getenv(provider_env_var, default_provider.value).lower()

        try:
            provider_type = LLMProviderType(provider_str)
        except ValueError:
            raise ValueError(f"Invalid provider type in {provider_env_var}: {provider_str}")

        # Get API key
        api_key = os.getenv(api_key_env_var)
        if not api_key:
            raise ValueError(f"Environment variable {api_key_env_var} is required")

        # Get model
        model = os.getenv(model_env_var, "openrouter/openai/gpt-4")

        # Additional config from environment
        extra_config = {}

        # Rate limiting
        if rpm := os.getenv("RATE_LIMIT_RPM"):
            extra_config["rate_limit_rpm"] = int(rpm)

        # OpenRouter specific config
        if provider_type == LLMProviderType.OPENROUTER:
            if referer := os.getenv("OPENROUTER_REFERER"):
                extra_config["referer"] = referer
            if title := os.getenv("OPENROUTER_TITLE"):
                extra_config["title"] = title

        return cls.create_provider(provider_type, api_key, model, **extra_config)

    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        """Get list of available providers with descriptions"""
        return {
            LLMProviderType.LITELLM.value: "LiteLLM provider (supports multiple LLM services)",
            LLMProviderType.OPENROUTER.value: "OpenRouter direct API provider"
        }
