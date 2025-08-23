"""
LiteLLM provider implementation
"""

import os
from typing import Dict, Any
import litellm
from .base import LLMProvider, LLMResponse


class LiteLLMProvider(LLMProvider):
    """LiteLLM-based LLM provider"""

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize LiteLLM provider with API key and model configuration."""
        super().__init__(api_key, model, **kwargs)
        self._setup_litellm()

    def _setup_litellm(self):
        """Setup LiteLLM configuration with API key and optional base URL."""
        litellm.api_key = self.api_key

        # Set additional configuration if provided
        if "base_url" in self.config:
            litellm.api_base = self.config["base_url"]

    def validate_config(self) -> bool:
        """Validate LiteLLM configuration including API key and model."""
        if not self.api_key:
            raise ValueError("API key is required for LiteLLM provider")

        if not self.model:
            raise ValueError("Model is required for LiteLLM provider")

        return True

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using LiteLLM with specified prompt and parameters."""
        self.validate_config()

        # Merge default kwargs with provided ones
        call_kwargs = {
            "temperature": 0.1,
            "max_tokens": 500,
            **kwargs
        }

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
                **call_kwargs
            )

            choice = response.choices[0]
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                }

            return LLMResponse(
                content=choice.message.content,
                model=self.model,
                usage=usage,
                finish_reason=getattr(choice, 'finish_reason', None)
            )

        except Exception as e:
            raise RuntimeError(f"LiteLLM generation failed: {e}") from e
