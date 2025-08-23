"""
Classification service for analyzing web content using LLM providers
"""
import json
import asyncio
from typing import Dict, List, Any
from pathlib import Path

from .models import ClassificationResult, LinkData
from .content_processor import ContentProcessor
from .llm import LLMProviderFactory


class ClassificationService:
    """Service for classifying web content using LLM providers"""

    def __init__(self, llm_provider=None):
        """Initialize classification service with specified LLM provider."""
        if llm_provider is None:
            self.llm_provider = LLMProviderFactory.from_env()
        else:
            self.llm_provider = llm_provider

        self.categories = [
            "Technology", "Science", "AI/ML", "Programming",
            "Research", "Tutorial", "News", "Blog", "Documentation",
            "Business", "Design", "Security", "Data Science", "Web Development"
        ]

        self.content_types = [
            "tutorial", "guide", "documentation", "research_paper",
            "blog_post", "news_article", "reference", "course", "tool"
        ]

    def get_classification_prompt(self, url: str, title: str, content: str) -> str:
        """Generate structured prompt for LLM content classification."""
        return f"""
Analyze the following web content and provide a structured classification.

URL: {url}
Title: {title}
Content: {content[:4000]}  # Truncated for API limits

Please respond with a JSON object containing:
{{
  "category": "primary category from: {', '.join(self.categories)}",
  "subcategory": "more specific subcategory",
  "tags": ["3-7 relevant tags"],
  "summary": "brief 2-3 sentence summary",
  "confidence": "confidence score 0.0-1.0",
  "content_type": "type from: {', '.join(self.content_types)}",
  "difficulty": "beginner/intermediate/advanced",
  "quality_score": "1-10 quality assessment",
  "key_topics": ["main topics covered"],
  "target_audience": "who this content is for"
}}

Be precise and objective in your analysis.
"""

    async def classify_content(self, url: str, title: str, content: str) -> ClassificationResult:
        """Classify web content using LLM and return structured result."""
        prompt = self.get_classification_prompt(url, title, content)

        try:
            print(f"Using LLM provider: {type(self.llm_provider).__name__}")
            async with self.llm_provider as provider:
                response = await provider.generate(
                    prompt,
                    temperature=0.7,
                    max_tokens=2048
                )

            result_text = response.content
            result_json = self.parse_llm_response(result_text)

            return ClassificationResult(**result_json)

        except Exception as e:
            print(f"Classification failed for {url}: {e}")
            return self.get_fallback_classification(url, title, content)

    def parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text and extract JSON classification data."""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                return self.parse_text_response(response_text)

        except json.JSONDecodeError:
            return self.parse_text_response(response_text)

    def parse_text_response(self, text: str) -> Dict[str, Any]:
        """Fallback parser for non-JSON LLM responses."""
        return {
            "category": "Technology",
            "subcategory": "General",
            "tags": ["web", "content"],
            "summary": text[:200] + "...",
            "confidence": 0.5,
            "content_type": "article",
            "difficulty": "intermediate",
            "quality_score": 5,
            "key_topics": ["general"],
            "target_audience": "general"
        }

    def get_fallback_classification(self, url: str, title: str, content: str) -> ClassificationResult:
        """Provide default classification when LLM classification fails."""
        return ClassificationResult(
            category="Technology",
            subcategory="General",
            tags=["web", "content"],
            summary=f"Content from {url}",
            confidence=0.3,
            content_type="article",
            difficulty="intermediate",
            quality_score=5,
            key_topics=["general"],
            target_audience="general"
        )

    async def classify_existing_links(self, index_file: Path = Path("index.json")) -> Dict[str, tuple]:
        """Classify all existing crawled links from index file."""
        if not index_file.exists():
            print(f"Index file {index_file} not found")
            return {}

        index_data = json.loads(index_file.read_text())
        classifications = {}

        for item in index_data:
            link = item.get("link")
            if not link:
                continue

            file_hash = item.get("id", ContentProcessor.hash_link(link))
            filename = item.get("filename")

            if not filename:
                continue

            file_path = Path("dat") / filename
            if not file_path.exists():
                print(f"File not found: {file_path}")
                continue

            content = ContentProcessor.extract_content_from_file(file_path)
            title = filename

            print(f"Classifying {link}...")
            classification = await self.classify_content(link, title, content)
            classifications[link] = (classification, file_hash)

            await asyncio.sleep(1)

        return classifications

    def save_classifications(self, classifications: Dict[str, tuple], 
                           output_file: Path = Path("classifications.json")):
        """Save classification results to JSON output file."""
        output_data = {}
        for link, (result, file_hash) in classifications.items():
            output_data[link] = {
                "hash": file_hash,
                "category": result.category,
                "subcategory": result.subcategory,
                "tags": result.tags,
                "summary": result.summary,
                "confidence": result.confidence,
                "content_type": result.content_type,
                "difficulty": result.difficulty,
                "quality_score": result.quality_score,
                "key_topics": result.key_topics,
                "target_audience": result.target_audience
            }

        output_file.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        print(f"Saved {len(classifications)} classifications to {output_file}")