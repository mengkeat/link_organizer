"""
Base LLM provider interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized LLM response structure"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize LLM provider with API key and model configuration."""
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.timeout = kwargs.get('timeout', 30)  # Default 30 second timeout

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from LLM given input prompt."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration and credentials."""
        pass

    async def __aenter__(self):
        """Async context manager entry for resource initialization."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit for resource cleanup."""
        pass
