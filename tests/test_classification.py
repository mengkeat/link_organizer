#!/usr/bin/env python3
"""
Test script for Link Classifier
Usage: python test_classification.py [options]
"""

import asyncio
import argparse
import sys
from pathlib import Path
from link_classifier import LinkClassifier

async def test_single_url():
    """Test classification with a single URL using sample content."""
    classifier = LinkClassifier()

    test_url = "https://example.com/ml-guide"
    test_title = "Machine Learning Guide"
    test_content = """
    Machine Learning is a subset of artificial intelligence that enables computers to learn and make decisions from data.
    This comprehensive guide covers supervised and unsupervised learning, neural networks, deep learning,
    and practical applications in computer vision, natural language processing, and robotics.
    You'll learn about popular algorithms like linear regression, decision trees, random forests,
    support vector machines, and convolutional neural networks. The guide includes Python code examples
    using scikit-learn, TensorFlow, and PyTorch libraries. Topics covered include data preprocessing,
    feature engineering, model evaluation, hyperparameter tuning, and deployment strategies.
    """

    print(f"Testing classification for: {test_url}")
    print("-" * 50)

    result = await classifier.classify_content(test_url, test_title, test_content)

    print(f"Category: {result.category}")
    print(f"Subcategory: {result.subcategory}")
    print(f"Content Type: {result.content_type}")
    print(f"Difficulty: {result.difficulty}")
    print(f"Quality Score: {result.quality_score}/10")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Target Audience: {result.target_audience}")
    print(f"Tags: {', '.join(result.tags)}")
    print(f"Key Topics: {', '.join(result.key_topics)}")
    print(f"Summary: {result.summary}")

async def classify_existing_links(limit: int = None, output_file: str = "classifications.json"):
    """Classify existing links from index.json with optional limit and output file."""
    classifier = LinkClassifier()

    print("Loading existing links from index.json...")
    classifications = await classifier.classify_existing_links()

    if limit:
        # Take first N items
        items = list(classifications.items())[:limit]
        classifications = dict(items)
        print(f"Limited to {limit} links for testing")

    if classifications:
        print(f"Classified {len(classifications)} links")
        classifier.save_classifications(classifications, Path(output_file))

        # Print summary
        categories = {}
        for result in classifications.values():
            cat = result.category
            categories[cat] = categories.get(cat, 0) + 1

        print("\nClassification Summary:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count}")
    else:
        print("No links found to classify")

async def interactive_classification():
    """Interactive mode for testing classification with user input."""
    classifier = LinkClassifier()

    print("Interactive Classification Mode")
    print("Enter URLs to classify (or 'quit' to exit)")

    while True:
        try:
            url = input("\nURL: ").strip()
            if url.lower() in ['quit', 'exit', 'q']:
                break
            if not url:
                continue

            title = input("Title: ").strip()
            content = input("Content (or press Enter to use URL): ").strip()

            if not content:
                content = f"Content from {url}"

            print("\nClassifying...")
            result = await classifier.classify_content(url, title, content)

            print(f"\nResults:")
            print(f"  Category: {result.category}")
            print(f"  Tags: {', '.join(result.tags)}")
            print(f"  Summary: {result.summary}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main entry point with command line argument parsing for test script."""
    parser = argparse.ArgumentParser(description="Test Link Classifier")
    parser.add_argument("--single", action="store_true", help="Test with single example")
    parser.add_argument("--existing", action="store_true", help="Classify existing links")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--limit", type=int, help="Limit number of links to classify")
    parser.add_argument("--output", default="classifications.json", help="Output file for classifications")

    args = parser.parse_args()

    if not any([args.single, args.existing, args.interactive]):
        args.single = True  # Default to single test

    try:
        if args.single:
            asyncio.run(test_single_url())
        elif args.existing:
            asyncio.run(classify_existing_links(args.limit, args.output))
        elif args.interactive:
            asyncio.run(interactive_classification())

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure your OPENROUTER_API_KEY is set in .env file")
        sys.exit(1)

if __name__ == "__main__":
    main()
