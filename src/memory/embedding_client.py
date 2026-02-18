"""
Thin wrapper around litellm for computing text embeddings.
"""

import os
from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers (allows easy test mocking)."""

    async def embed(self, text: str) -> np.ndarray: ...


class LiteLLMEmbeddingClient:
    """Embedding client using litellm."""

    def __init__(
        self,
        model: str = "openrouter/openai/text-embedding-3-small",
        api_key: str | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")

    async def embed(self, text: str) -> np.ndarray:
        """Compute embedding for text using litellm."""
        import litellm

        response = await litellm.aembedding(
            model=self.model,
            input=[text[:8000]],
            api_key=self.api_key,
        )
        vector = response.data[0]["embedding"]
        return np.array(vector, dtype=np.float64)
