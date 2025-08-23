"""
OpenRouter direct provider implementation
"""

import aiohttp
import json
from typing import Dict, Any
from .base import LLMProvider, LLMResponse


class OpenRouterProvider(LLMProvider):
    """OpenRouter direct API provider"""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize OpenRouter provider with API key and model configuration."""
        super().__init__(api_key, model, **kwargs)
        self.session = None

    def validate_config(self) -> bool:
        """Validate OpenRouter configuration including API key and model."""
        if not self.api_key:
            raise ValueError("API key is required for OpenRouter provider")

        if not self.model:
            raise ValueError("Model is required for OpenRouter provider")

        # Ensure model starts with openrouter/ if not already
        # if not self.model.startswith("openrouter/"):
        #     self.model = f"openrouter/{self.model}"

        return True

    async def __aenter__(self):
        """Setup async HTTP session for API requests."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP session resources."""
        if self.session:
            await self.session.close()
            self.session = None

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using OpenRouter direct API with specified prompt."""
        self.validate_config()

        if not self.session:
            await self.__aenter__()

        # Merge default kwargs with provided ones
        call_kwargs = {
            "temperature": 0.7,
            "max_tokens": 2048,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.get("referer", "https://github.com/your-app"),
            "X-Title": self.config.get("title", "Link Organizer")
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **call_kwargs
        }

        try:
            async with self.session.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()

                choice = data["choices"][0]
                usage = data.get("usage")

                return LLMResponse(
                    content=choice["message"]["content"],
                    model=data.get("model", self.model),
                    usage=usage,
                    finish_reason=choice.get("finish_reason")
                )

        except aiohttp.ClientError as e:
            raise RuntimeError(f"OpenRouter API request failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"OpenRouter generation failed: {e}") from e
