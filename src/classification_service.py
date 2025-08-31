"""
Classification service for analyzing web content using LLM providers
"""
import json
import asyncio
from typing import Dict, Any

from .models import ClassificationResult as ClassificationResultModel
from .database import Session, LinkData, ClassificationResult
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

    async def classify_link_data(self, link_data: LinkData) -> ClassificationResultModel:
        """Classify web content using LLM and return structured result."""
        prompt = self.get_classification_prompt(link_data.link, link_data.filename, link_data.content)

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

            return ClassificationResultModel(**result_json)

        except Exception as e:
            print(f"Classification failed for {link_data.link}: {e}")
            return self.get_fallback_classification(link_data.link, link_data.filename, link_data.content)

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

    def get_fallback_classification(self, url: str, title: str, content: str) -> ClassificationResultModel:
        """Provide default classification when LLM classification fails."""
        return ClassificationResultModel(
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

    async def classify_pending_links(self, session=None):
        """Classify all existing crawled links from the database."""
        if session is None:
            session = Session()
            close_session = True
        else:
            close_session = False

        try:
            pending_links = session.query(LinkData).filter(LinkData.status == "Success", LinkData.classification == None).all()

            for link_data in pending_links:
                print(f"Classifying {link_data.link}...")
                classification_result_model = await self.classify_link_data(link_data)
                
                classification_result = ClassificationResult(
                    category=classification_result_model.category,
                    subcategory=classification_result_model.subcategory,
                    tags=classification_result_model.tags,
                    summary=classification_result_model.summary,
                    confidence=classification_result_model.confidence,
                    content_type=classification_result_model.content_type,
                    difficulty=classification_result_model.difficulty,
                    quality_score=classification_result_model.quality_score,
                    key_topics=classification_result_model.key_topics,
                    target_audience=classification_result_model.target_audience
                )

                link_data.classification = classification_result
                link_data.status = "classified"
                session.commit()
                print(f"Successfully classified {link_data.link}")

                await asyncio.sleep(1)
        finally:
            if close_session:
                session.close()
