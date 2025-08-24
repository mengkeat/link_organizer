#!/usr/bin/env python3
"""
Example usage of the modular LLM interface
Demonstrates how to use different providers with LinkClassifier
"""

import asyncio
import os
from link_classifier import LinkClassifier
from src.llm import LLMProviderFactory, LiteLLMProvider, OpenRouterProvider


async def example_with_factory():
    """Example using the factory pattern with environment configuration."""
    print("=== Example 1: Using Factory with Environment Configuration ===")

    # Create provider from environment (as configured in .env)
    provider = LLMProviderFactory.from_env()
    print(f"Created provider: {type(provider).__name__}")
    print(f"Model: {provider.model}")

    # Create classifier with the provider
    classifier = LinkClassifier(llm_provider=provider)

    # Test classification
    test_url = "https://example.com/python-tutorial"
    test_title = "Python Machine Learning Tutorial"
    test_content = """
    This comprehensive tutorial covers machine learning with Python.
    Learn about neural networks, deep learning, and practical applications.
    Includes code examples with TensorFlow and PyTorch.
    """

    print(f"Classifying: {test_url}")
    result = await classifier.classify_content(test_url, test_title, test_content)

    print(f"Category: {result.category}")
    print(f"Subcategory: {result.subcategory}")
    print(f"Tags: {', '.join(result.tags)}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Content Type: {result.content_type}")
    print(f"Difficulty: {result.difficulty}")
    print()


async def example_with_specific_providers():
    """Example using specific LLM providers directly instead of factory."""
    print("=== Example 2: Using Specific Providers ===")

    # Get API key from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Please set OPENROUTER_API_KEY in your .env file")
        return

    # Test with LiteLLM provider
    print("Testing with LiteLLM provider...")
    litellm_provider = LiteLLMProvider(api_key, "gpt-4")
    classifier1 = LinkClassifier(llm_provider=litellm_provider)

    # Test with OpenRouter provider
    print("Testing with OpenRouter provider...")
    openrouter_provider = OpenRouterProvider(api_key, "openrouter/openai/gpt-4")
    classifier2 = LinkClassifier(llm_provider=openrouter_provider)

    # Test content
    test_url = "https://example.com/web-development"
    test_title = "Modern Web Development Guide"
    test_content = """
    Learn modern web development with React, Node.js, and cloud technologies.
    This guide covers frontend frameworks, backend APIs, databases, and deployment.
    Includes practical examples and best practices for building scalable applications.
    """

    print(f"Classifying: {test_url}")

    # Test LiteLLM
    print("\n--- LiteLLM Provider ---")
    try:
        async with litellm_provider as provider:
            result1 = await classifier1.classify_content(test_url, test_title, test_content)
            print(f"Category: {result1.category}")
            print(f"Tags: {', '.join(result1.tags)}")
            print(f"Content Type: {result1.content_type}")
    except Exception as e:
        print(f"LiteLLM Error: {e}")

    # Test OpenRouter
    print("\n--- OpenRouter Provider ---")
    try:
        async with openrouter_provider as provider:
            result2 = await classifier2.classify_content(test_url, test_title, test_content)
            print(f"Category: {result2.category}")
            print(f"Tags: {', '.join(result2.tags)}")
            print(f"Content Type: {result2.content_type}")
    except Exception as e:
        print(f"OpenRouter Error: {e}")

    print()


async def example_provider_switching():
    """Example of switching between different LLM providers for comparison."""
    print("=== Example 3: Provider Switching ===")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Please set OPENROUTER_API_KEY in your .env file")
        return

    # Test content
    test_url = "https://example.com/data-science"
    test_title = "Data Science Fundamentals"
    test_content = """
    Introduction to data science covering statistics, machine learning algorithms,
    data visualization, and big data processing. Learn Python data science stack
    including pandas, numpy, scikit-learn, and matplotlib.
    """

    # Create different providers
    providers = {
        "LiteLLM": LiteLLMProvider(api_key, "gpt-4"),
        "OpenRouter": OpenRouterProvider(api_key, "openrouter/openai/gpt-4")
    }

    print(f"Classifying: {test_url}")

    for name, provider in providers.items():
        print(f"\n--- {name} Provider ---")
        try:
            classifier = LinkClassifier(llm_provider=provider)
            result = await classifier.classify_content(test_url, test_title, test_content)
            print(f"Category: {result.category}")
            print(f"Subcategory: {result.subcategory}")
            print(f"Quality Score: {result.quality_score}/10")
            print(f"Target Audience: {result.target_audience}")
        except Exception as e:
            print(f"Error with {name}: {e}")

    print()


async def example_available_providers():
    """Example of listing all available LLM providers and descriptions."""
    print("=== Example 4: Available Providers ===")

    providers = LLMProviderFactory.get_available_providers()

    print("Available LLM Providers:")
    for provider_type, description in providers.items():
        print(f"  - {provider_type}: {description}")

    print()


async def main():
    """Main function to run all LLM provider examples sequentially."""
    print("LLM Interface Examples")
    print("=" * 50)

    # Check if API key is available
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Warning: OPENROUTER_API_KEY not found in environment.")
        print("Some examples may not work without a valid API key.")
        print("Please set it in your .env file.")
        print()

    try:
        await example_available_providers()
        await example_with_factory()

        # Only run provider-specific examples if API key is available
        if os.getenv("OPENROUTER_API_KEY"):
            await example_with_specific_providers()
            await example_provider_switching()
        else:
            print("Skipping provider-specific examples (no API key)")

    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure your .env file is properly configured.")


if __name__ == "__main__":
    asyncio.run(main())
