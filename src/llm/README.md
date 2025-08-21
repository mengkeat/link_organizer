# Modular LLM Interface

This module provides a modular and extensible interface for integrating different LLM providers into the Link Organizer project. It supports multiple providers with a consistent API, making it easy to switch between services or add new ones.

## Features

- **Modular Design**: Abstract base class with concrete implementations
- **Multiple Providers**: Support for LiteLLM and OpenRouter direct API
- **Consistent Interface**: All providers implement the same methods
- **Easy Configuration**: Environment-based configuration with factory pattern
- **Error Handling**: Robust error handling with fallback mechanisms
- **Async Support**: Full async/await support with context managers
- **Type Safety**: Full type hints and validation

## Architecture

```
src/llm/
├── base.py              # Abstract base class and response types
├── factory.py           # Provider factory for easy instantiation
├── litellm_provider.py  # LiteLLM implementation
├── openrouter_provider.py  # OpenRouter direct API implementation
└── __init__.py          # Package exports
```

### Key Components

1. **LLMProvider (Abstract Base)**: Defines the interface all providers must implement
2. **LLMResponse**: Standardized response structure
3. **LLMProviderFactory**: Factory class for creating providers from configuration
4. **Concrete Providers**: Specific implementations for each LLM service

## Usage

### Basic Usage

```python
from src.llm import LLMProviderFactory

# Create provider from environment variables
provider = LLMProviderFactory.from_env()

# Use with context manager
async with provider as p:
    response = await p.generate("Your prompt here")
    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Usage: {response.usage}")
```

### Creating Specific Providers

```python
from src.llm import LLMProviderType, LiteLLMProvider, OpenRouterProvider

# Create LiteLLM provider
litellm_provider = LLMProviderFactory.create_provider(
    LLMProviderType.LITELLM,
    api_key="your-api-key",
    model="gpt-4"
)

# Create OpenRouter provider
openrouter_provider = LLMProviderFactory.create_provider(
    LLMProviderType.OPENROUTER,
    api_key="your-api-key",
    model="openrouter/openai/gpt-4"
)
```

### Configuration

The providers can be configured using environment variables:

```bash
# Choose provider (litellm or openrouter)
LLM_PROVIDER=litellm

# API key (required for both providers)
OPENROUTER_API_KEY=your-api-key-here

# Model selection
LITELLM_MODEL=gpt-4

# Rate limiting
RATE_LIMIT_RPM=30

# OpenRouter specific (optional)
OPENROUTER_REFERER=https://your-app.com
OPENROUTER_TITLE=Your App Name
```

## Providers

### LiteLLM Provider

The LiteLLM provider uses the [LiteLLM](https://litellm.ai/) library to support multiple LLM services through a unified interface.

**Features:**
- Supports 100+ LLM providers
- Unified pricing and token counting
- Automatic retries and fallbacks
- Advanced features like streaming, function calling

**Example:**
```python
provider = LiteLLMProvider(
    api_key="your-api-key",
    model="gpt-4",
    base_url="https://api.openai.com/v1"  # Optional
)
```

### OpenRouter Provider

The OpenRouter provider connects directly to the [OpenRouter](https://openrouter.ai/) API for fast, reliable access to multiple models.

**Features:**
- Direct API access (no middleware)
- Lower latency
- OpenRouter-specific features
- Custom routing and fallbacks

**Example:**
```python
provider = OpenRouterProvider(
    api_key="your-api-key",
    model="openrouter/openai/gpt-4",
    referer="https://your-app.com",  # Optional
    title="Your App Name"            # Optional
)
```

## Integration with LinkClassifier

The modular interface is already integrated with the LinkClassifier:

```python
from link_classifier import LinkClassifier

# Uses provider from environment automatically
classifier = LinkClassifier()

# Or specify custom provider
from src.llm import LiteLLMProvider
custom_provider = LiteLLMProvider("key", "gpt-4")
classifier = LinkClassifier(llm_provider=custom_provider)

# Classify content
result = await classifier.classify_content(url, title, content)
```

## Error Handling

The interface includes comprehensive error handling:

```python
async with provider as p:
    try:
        response = await p.generate("Prompt")
        # Process response
    except ValueError as e:
        # Configuration error
        print(f"Config error: {e}")
    except RuntimeError as e:
        # API or network error
        print(f"Runtime error: {e}")
    except Exception as e:
        # Unexpected error
        print(f"Unexpected error: {e}")
```

## Testing

Run the tests with pytest:

```bash
# Test all LLM providers
pytest tests/test_llm_providers.py

# Test LinkClassifier integration
pytest tests/test_link_classifier.py

# Run with verbose output
pytest tests/ -v
```

### Mocking for Tests

```python
from unittest.mock import AsyncMock, patch
from src.llm import LLMResponse

# Mock provider response
mock_response = LLMResponse(
    content="Mocked response",
    model="test-model",
    usage={"prompt_tokens": 10, "completion_tokens": 5}
)

with patch.object(provider, 'generate', new_callable=AsyncMock) as mock_generate:
    mock_generate.return_value = mock_response
    response = await provider.generate("Test prompt")
```

## Adding New Providers

To add a new LLM provider:

1. **Create Provider Class**: Inherit from `LLMProvider`

```python
from src.llm.base import LLMProvider, LLMResponse

class NewProvider(LLMProvider):
    def validate_config(self) -> bool:
        # Validate your configuration
        pass

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        # Implement generation logic
        pass
```

2. **Register with Factory**: Add to `LLMProviderFactory.PROVIDERS`

```python
from src.llm.factory import LLMProviderFactory, LLMProviderType

# Add new provider type
LLMProviderType.NEW_PROVIDER = "new_provider"

# Register provider class
LLMProviderFactory.PROVIDERS[LLMProviderType.NEW_PROVIDER] = NewProvider
```

3. **Add Tests**: Create comprehensive tests in `tests/`

## Best Practices

1. **Always use context managers** for proper resource cleanup
2. **Handle exceptions** appropriately with fallbacks
3. **Validate configuration** before making API calls
4. **Use environment variables** for configuration in production
5. **Add comprehensive tests** for new providers
6. **Monitor usage and costs** through the usage tracking features

## Contributing

When contributing new providers:

1. Follow the existing patterns and interfaces
2. Add comprehensive tests with mocking
3. Include documentation and examples
4. Handle errors gracefully with meaningful messages
5. Support both sync and async usage where applicable

## License

This module is part of the Link Organizer project and follows the same license terms.
