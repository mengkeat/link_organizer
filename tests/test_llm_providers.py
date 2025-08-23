"""
Tests for LLM providers
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm.base import LLMProvider, LLMResponse
from src.llm.litellm_provider import LiteLLMProvider
from src.llm.openrouter_provider import OpenRouterProvider
from src.llm.factory import LLMProviderFactory, LLMProviderType


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_llm_response_creation(self):
        """Test creating LLMResponse with all fields."""
        response = LLMResponse(
            content="Test response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            finish_reason="stop"
        )

        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.usage == {"prompt_tokens": 10, "completion_tokens": 5}
        assert response.finish_reason == "stop"

    def test_llm_response_defaults(self):
        """Test LLMResponse with default values"""
        response = LLMResponse(content="Test", model="test")

        assert response.usage is None
        assert response.finish_reason is None


class TestLLMProvider:
    """Test base LLMProvider class"""

    def test_abstract_methods(self):
        """Test that base class requires implementation of abstract methods"""
        with pytest.raises(TypeError):
            LLMProvider("test_key", "test_model")

    def test_context_manager(self):
        """Test async context manager methods"""
        provider = LiteLLMProvider("test_key", "test_model")

        # Test that context manager methods exist
        assert hasattr(provider, "__aenter__")
        assert hasattr(provider, "__aexit__")


class TestLiteLLMProvider:
    """Test LiteLLM provider"""

    def test_initialization(self):
        """Test LiteLLM provider initialization with API key and model."""
        provider = LiteLLMProvider("test_key", "test_model")

        assert provider.api_key == "test_key"
        assert provider.model == "test_model"
        assert provider.config == {}

    def test_initialization_with_config(self):
        """Test initialization with additional config"""
        config = {"base_url": "https://test.com", "timeout": 30}
        provider = LiteLLMProvider("test_key", "test_model", **config)

        assert provider.config == config

    def test_validate_config_success(self):
        """Test successful config validation"""
        provider = LiteLLMProvider("test_key", "test_model")
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        """Test config validation with missing API key"""
        provider = LiteLLMProvider("", "test_model")

        with pytest.raises(ValueError, match="API key is required"):
            provider.validate_config()

    def test_validate_config_missing_model(self):
        """Test config validation with missing model"""
        provider = LiteLLMProvider("test_key", "")

        with pytest.raises(ValueError, match="Model is required"):
            provider.validate_config()

    @patch('litellm.acompletion')
    async def test_generate_success(self, mock_acompletion):
        """Test successful generation"""
        # Mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated response"
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_acompletion.return_value = mock_response

        provider = LiteLLMProvider("test_key", "test_model")
        response = await provider.generate("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.content == "Generated response"
        assert response.model == "test_model"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
        assert response.finish_reason == "stop"

        mock_acompletion.assert_called_once_with(
            model="test_model",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.1,
            max_tokens=500
        )

    @patch('litellm.acompletion')
    async def test_generate_with_custom_params(self, mock_acompletion):
        """Test generation with custom parameters"""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_response.choices = [mock_choice]
        mock_acompletion.return_value = mock_response

        provider = LiteLLMProvider("test_key", "test_model")
        await provider.generate("Test prompt", temperature=0.5, max_tokens=100)

        mock_acompletion.assert_called_once_with(
            model="test_model",
            messages=[{"role": "user", "content": "Test prompt"}],
            temperature=0.5,
            max_tokens=100
        )

    @patch('litellm.acompletion')
    async def test_generate_missing_usage(self, mock_acompletion):
        """Test generation when usage info is missing"""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_acompletion.return_value = mock_response

        provider = LiteLLMProvider("test_key", "test_model")
        response = await provider.generate("Test prompt")

        assert response.usage is None


class TestOpenRouterProvider:
    """Test OpenRouter provider"""

    def test_initialization(self):
        """Test OpenRouter provider initialization with API key and model."""
        provider = OpenRouterProvider("test_key", "gpt-4")

        assert provider.api_key == "test_key"
        assert provider.model == "openrouter/gpt-4"
        assert provider.session is None

    def test_initialization_with_openrouter_prefix(self):
        """Test initialization with model already having openrouter prefix"""
        provider = OpenRouterProvider("test_key", "openrouter/gpt-4")

        assert provider.model == "openrouter/gpt-4"

    def test_validate_config_success(self):
        """Test successful config validation"""
        provider = OpenRouterProvider("test_key", "gpt-4")
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        """Test config validation with missing API key"""
        provider = OpenRouterProvider("", "gpt-4")

        with pytest.raises(ValueError, match="API key is required"):
            provider.validate_config()

    def test_validate_config_missing_model(self):
        """Test config validation with missing model"""
        provider = OpenRouterProvider("test_key", "")

        with pytest.raises(ValueError, match="Model is required"):
            provider.validate_config()

    @patch('aiohttp.ClientSession.post')
    async def test_generate_success(self, mock_post):
        """Test successful generation with OpenRouter"""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Generated response"}, "finish_reason": "stop"}],
            "model": "openrouter/gpt-4",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        })
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = OpenRouterProvider("test_key", "gpt-4")

        async with provider as p:
            response = await p.generate("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.content == "Generated response"
        assert response.model == "openrouter/gpt-4"
        assert response.usage == {"prompt_tokens": 10, "completion_tokens": 5}
        assert response.finish_reason == "stop"

    async def test_context_manager(self):
        """Test async context manager"""
        provider = OpenRouterProvider("test_key", "gpt-4")

        async with provider as p:
            assert p.session is not None

        # Session should be closed after exiting context
        assert provider.session is None


class TestLLMProviderFactory:
    """Test LLM provider factory"""

    def test_create_litellm_provider(self):
        """Test creating LiteLLM provider"""
        provider = LLMProviderFactory.create_provider(
            LLMProviderType.LITELLM,
            "test_key",
            "gpt-4"
        )

        assert isinstance(provider, LiteLLMProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "gpt-4"

    def test_create_openrouter_provider(self):
        """Test creating OpenRouter provider"""
        provider = LLMProviderFactory.create_provider(
            LLMProviderType.OPENROUTER,
            "test_key",
            "gpt-4"
        )

        assert isinstance(provider, OpenRouterProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "openrouter/gpt-4"

    def test_create_unknown_provider(self):
        """Test creating unknown provider type"""
        with pytest.raises(ValueError, match="Unknown provider type"):
            LLMProviderFactory.create_provider("unknown", "test_key", "gpt-4")

    @patch.dict(os.environ, {
        'OPENROUTER_API_KEY': 'test_key',
        'LITELLM_MODEL': 'gpt-4',
        'LLM_PROVIDER': 'litellm'
    })
    def test_from_env_litellm(self):
        """Test creating provider from environment - LiteLLM"""
        provider = LLMProviderFactory.from_env()

        assert isinstance(provider, LiteLLMProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "gpt-4"

    @patch.dict(os.environ, {
        'OPENROUTER_API_KEY': 'test_key',
        'LITELLM_MODEL': 'gpt-4',
        'LLM_PROVIDER': 'openrouter'
    })
    def test_from_env_openrouter(self):
        """Test creating provider from environment - OpenRouter"""
        provider = LLMProviderFactory.from_env()

        assert isinstance(provider, OpenRouterProvider)
        assert provider.api_key == "test_key"
        assert provider.model == "openrouter/gpt-4"

    @patch.dict(os.environ, {
        'OPENROUTER_API_KEY': 'test_key',
        'LITELLM_MODEL': 'gpt-4'
    })
    def test_from_env_default(self):
        """Test creating provider from environment with default"""
        provider = LLMProviderFactory.from_env()

        assert isinstance(provider, LiteLLMProvider)  # Default provider

    @patch.dict(os.environ, {
        'OPENROUTER_API_KEY': 'test_key',
        'LITELLM_MODEL': 'gpt-4',
        'LLM_PROVIDER': 'invalid'
    })
    def test_from_env_invalid_provider(self):
        """Test creating provider from environment with invalid provider"""
        with pytest.raises(ValueError, match="Invalid provider type"):
            LLMProviderFactory.from_env()

    @patch.dict(os.environ, {
        'LITELLM_MODEL': 'gpt-4',
        'LLM_PROVIDER': 'litellm'
    })
    def test_from_env_missing_api_key(self):
        """Test creating provider from environment with missing API key"""
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY is required"):
            LLMProviderFactory.from_env()

    def test_get_available_providers(self):
        """Test getting available providers"""
        providers = LLMProviderFactory.get_available_providers()

        assert "litellm" in providers
        assert "openrouter" in providers
        assert providers["litellm"] == "LiteLLM provider (supports multiple LLM services)"
        assert providers["openrouter"] == "OpenRouter direct API provider"
