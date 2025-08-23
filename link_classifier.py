"""
Link Classifier with modular LLM interface
Provides automatic categorization, tagging, and summarization of web content
Supports multiple LLM providers (LiteLLM and OpenRouter direct)
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

from src.classification_service import ClassificationService
from src.models import ClassificationResult

# Load environment variables
load_dotenv()

class LinkClassifier(ClassificationService):
    """Main classifier - now a thin wrapper around ClassificationService for backwards compatibility"""
    pass

async def main():
    """Main function for testing link classification with sample content."""
    classifier = LinkClassifier()

    test_url = "https://example.com"
    test_title = "Example Article"
    test_content = """
    This is a comprehensive guide to machine learning and artificial intelligence.
    It covers neural networks, deep learning, and practical applications in technology.
    The article includes code examples in Python and discusses best practices for ML engineers.
    """

    print("Testing classification...")
    result = await classifier.classify_content(test_url, test_title, test_content)

    print(f"Category: {result.category}")
    print(f"Tags: {result.tags}")
    print(f"Summary: {result.summary}")
    print(f"Confidence: {result.confidence}")
    print(f"\n\nComplete Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
