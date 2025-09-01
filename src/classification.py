"""
Simplified Classification Service for analyzing web content
"""
import json
import asyncio
from typing import Dict, Any

from .models import ClassificationResult
from .llm import LLMProviderFactory


class ClassificationService:
    """Simplified service for classifying web content using LLM providers"""

    def __init__(self, llm_provider=None):
        """Initialize classification service with specified LLM provider."""
        if llm_provider is None:
            self.llm_provider = LLMProviderFactory.from_env()
        else:
            self.llm_provider = llm_provider

    def get_classification_prompt(self, url: str, title: str, content: str) -> str:
        """Generate structured prompt for LLM content classification."""
        categories = [
            "Technology", "Science", "AI/ML", "Programming",
            "Research", "Tutorial", "News", "Blog", "Documentation",
            "Business", "Design", "Security", "Data Science", "Web Development"
        ]
        
        content_types = [
            "tutorial", "guide", "documentation", "research_paper",
            "blog_post", "news_article", "reference", "course", "tool"
        ]
        
        return f"""
Analyze the following web content and provide a structured classification.

URL: {url}
Title: {title}
Content: {content[:4000]}

Please respond with a JSON object containing:
{{
  "category": "primary category from: {', '.join(categories)}",
  "subcategory": "more specific subcategory",
  "tags": ["3-7 relevant tags"],
  "summary": "brief 2-3 sentence summary",
  "confidence": "confidence score 0.0-1.0",
  "content_type": "type from: {', '.join(content_types)}",
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
            async with self.llm_provider as provider:
                response = await provider.generate(
                    prompt,
                    temperature=0.7,
                    max_tokens=2048
                )

            result_text = response.content
            result_json = self._parse_llm_response(result_text)
            return ClassificationResult(**result_json)

        except Exception as e:
            print(f"Classification failed for {url}: {e}")
            return self._get_fallback_classification(url)

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text and extract JSON classification data."""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                return self._get_fallback_data()

        except json.JSONDecodeError:
            return self._get_fallback_data()

    def _get_fallback_data(self) -> Dict[str, Any]:
        """Fallback data structure for failed parsing."""
        return {
            "category": "Technology",
            "subcategory": "General",
            "tags": ["web", "content"],
            "summary": "Content classification failed",
            "confidence": 0.3,
            "content_type": "article",
            "difficulty": "intermediate",
            "quality_score": 5,
            "key_topics": ["general"],
            "target_audience": "general"
        }

    def _get_fallback_classification(self, url: str) -> ClassificationResult:
        """Provide default classification when LLM classification fails."""
        data = self._get_fallback_data()
        data["summary"] = f"Content from {url}"
        return ClassificationResult(**data)