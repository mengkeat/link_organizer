"""
Shared test fixtures for crawler and classification tests
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from src.models import ClassificationResult, LinkData
from src.link_index import IndexEntry, LinkIndex


@dataclass
class MockCrawlResult:
    """Mock result from AsyncWebCrawler"""
    success: bool
    markdown: Optional[str] = None
    screenshot: Optional[str] = None


class MockAsyncWebCrawler:
    """Mock AsyncWebCrawler for testing"""

    def __init__(self, results: Optional[Dict[str, MockCrawlResult]] = None):
        self.results = results or {}
        self.default_result = MockCrawlResult(
            success=True,
            markdown="# Test Content\n\nThis is test markdown content.",
            screenshot="base64encodedscreenshot"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def arun(self, url: str, config=None):
        return self.results.get(url, self.default_result)


def create_mock_crawler_result(
    success: bool = True,
    markdown: str = "# Test Content\n\nThis is test content.",
    screenshot: Optional[str] = None
) -> MockCrawlResult:
    """Create a mock crawler result"""
    return MockCrawlResult(
        success=success,
        markdown=markdown,
        screenshot=screenshot
    )


def create_mock_classification_result(
    category: str = "Technology",
    subcategory: str = "Programming",
    tags: Optional[List[str]] = None,
    summary: str = "Test summary",
    confidence: float = 0.85,
    content_type: str = "tutorial",
    difficulty: str = "intermediate",
    quality_score: int = 7,
    key_topics: Optional[List[str]] = None,
    target_audience: str = "developers"
) -> ClassificationResult:
    """Create a mock classification result"""
    return ClassificationResult(
        category=category,
        subcategory=subcategory,
        tags=tags or ["python", "testing"],
        summary=summary,
        confidence=confidence,
        content_type=content_type,
        difficulty=difficulty,
        quality_score=quality_score,
        key_topics=key_topics or ["unit testing", "mocking"],
        target_audience=target_audience
    )


def create_mock_index_entry(
    link: str = "https://example.com/test",
    status: str = "Success",
    readable_filename: Optional[str] = "example-test.md",
    classification: Optional[Dict[str, Any]] = None
) -> IndexEntry:
    """Create a mock index entry"""
    link_id = f"test_id_{hash(link) % 10000}"
    return IndexEntry(
        link=link,
        id=link_id,
        filename=f"{link_id}.md",
        readable_filename=readable_filename,
        status=status,
        crawled_at=datetime.now().isoformat(),
        classification=classification or {
            "category": "Technology",
            "subcategory": "Programming",
            "tags": ["python"],
            "summary": "Test summary",
            "confidence": 0.85,
            "content_type": "tutorial",
            "difficulty": "intermediate",
            "quality_score": 7,
            "key_topics": ["testing"],
            "target_audience": "developers"
        }
    )


def create_mock_link_data(
    link: str = "https://example.com/test",
    content: str = "Test content for classification",
    status: str = "Fetched"
) -> LinkData:
    """Create a mock LinkData object"""
    link_id = f"test_id_{hash(link) % 10000}"
    link_data = LinkData(
        link=link,
        id=link_id,
        filename=f"{link_id}.md",
        content=content,
        status=status
    )
    return link_data


class MockClassificationService:
    """Mock ClassificationService for testing"""

    def __init__(self, results: Optional[Dict[str, ClassificationResult]] = None):
        self.results = results or {}
        self.default_result = create_mock_classification_result()
        self.classify_calls = []

    async def classify_content(self, url: str, title: str, content: str) -> ClassificationResult:
        self.classify_calls.append((url, title, content))
        return self.results.get(url, self.default_result)


def create_temp_index(tmp_path: Path, entries: Optional[List[IndexEntry]] = None) -> LinkIndex:
    """Create a temporary index file for testing"""
    index_file = tmp_path / "test_index.json"

    if entries:
        data = [entry.to_dict() for entry in entries]
        index_file.write_text(json.dumps(data, indent=2))
    else:
        index_file.write_text("[]")

    return LinkIndex(index_file)


def create_temp_index_with_links(tmp_path: Path, links: List[str], statuses: Optional[List[str]] = None) -> LinkIndex:
    """Create a temporary index with specified links and statuses"""
    statuses = statuses or ["Success"] * len(links)
    entries = []
    for link, status in zip(links, statuses):
        entries.append(create_mock_index_entry(link=link, status=status))
    return create_temp_index(tmp_path, entries)


SAMPLE_URLS = [
    "https://example.com/article1",
    "https://github.com/user/repo",
    "https://arxiv.org/abs/2105.00613",
    "https://blog.example.com/posts/test-post",
    "https://docs.python.org/3/tutorial/",
]

SAMPLE_PDF_URLS = [
    "https://arxiv.org/pdf/2105.00613.pdf",
    "https://example.com/document.pdf",
]

SAMPLE_MARKDOWN_CONTENT = """
# Sample Article

This is a test article about Python programming.

## Introduction

Python is a versatile programming language.

## Code Example

```python
def hello_world():
    print("Hello, World!")
```

## Conclusion

Python is great for beginners and experts alike.
"""

SAMPLE_CLASSIFICATION_JSON = {
    "category": "Technology",
    "subcategory": "Programming",
    "tags": ["python", "tutorial", "programming"],
    "summary": "A beginner's guide to Python programming",
    "confidence": 0.92,
    "content_type": "tutorial",
    "difficulty": "beginner",
    "quality_score": 8,
    "key_topics": ["python", "programming basics"],
    "target_audience": "beginners"
}
