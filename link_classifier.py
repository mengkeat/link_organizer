"""
Link Classifier using LiteLLM with OpenRouter
Provides automatic categorization, tagging, and summarization of web content
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import litellm
from dotenv import load_dotenv
import PyPDF2
import hashlib

# Load environment variables
load_dotenv()

@dataclass
class ClassificationResult:
    """Structured classification result"""
    category: str
    subcategory: str
    tags: List[str]
    summary: str
    confidence: float
    content_type: str
    difficulty: str
    quality_score: int
    key_topics: List[str]
    target_audience: str

class LinkClassifier:
    """Main classifier using LiteLLM with OpenRouter"""

    def __init__(self, model: str = "openrouter/gpt-4"):
        """Initialize classifier with specified model"""
        self.model = model
        self.api_key = os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        # Set up LiteLLM
        litellm.api_key = self.api_key

        # Define classification categories
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
        """Generate structured classification prompt"""
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
        """Classify content using LLM"""
        prompt = self.get_classification_prompt(url, title, content)

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            result_json = self.parse_llm_response(result_text)

            return ClassificationResult(**result_json)

        except Exception as e:
            print(f"Classification failed for {url}: {e}")
            return self.get_fallback_classification(url, title, content)

    def parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response, handling various formats"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                # Fallback parsing for non-JSON responses
                return self.parse_text_response(response_text)

        except json.JSONDecodeError:
            return self.parse_text_response(response_text)

    def parse_text_response(self, text: str) -> Dict[str, Any]:
        """Fallback parser for non-JSON responses"""
        # Simple extraction - in production you'd want more sophisticated parsing
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
        """Provide fallback classification when LLM fails"""
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

    def extract_content_from_file(self, file_path: Path) -> str:
        """Extract text content from markdown or PDF files"""
        try:
            if file_path.suffix.lower() == '.md':
                return file_path.read_text(encoding='utf-8')
            elif file_path.suffix.lower() == '.pdf':
                return self.extract_pdf_text(file_path)
            else:
                return f"Unsupported file type: {file_path.suffix}"
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF files"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            return f"Error extracting PDF text: {e}"

    def hash_link(self, link: str) -> str:
        """Generate hash for link (matching existing system)"""
        return hashlib.sha256(link.encode("utf-8")).hexdigest()

    async def classify_existing_links(self, index_file: Path = Path("index.json")) -> Dict[str, ClassificationResult]:
        """Classify all existing links from index.json"""
        if not index_file.exists():
            print(f"Index file {index_file} not found")
            return {}

        index_data = json.loads(index_file.read_text())
        classifications = {}

        for item in index_data:
            link = item.get("link")
            if not link:
                continue

            file_hash = item.get("id", self.hash_link(link))
            filename = item.get("filename")

            if not filename:
                continue

            file_path = Path("dat") / filename
            if not file_path.exists():
                print(f"File not found: {file_path}")
                continue

            # Extract content
            content = self.extract_content_from_file(file_path)
            title = filename  # Use filename as title if no better option

            # Classify
            print(f"Classifying {link}...")
            classification = await self.classify_content(link, title, content)
            classifications[link] = classification

            # Small delay to respect API limits
            await asyncio.sleep(1)

        return classifications

    def save_classifications(self, classifications: Dict[str, ClassificationResult], output_file: Path = Path("classifications.json")):
        """Save classifications to JSON file"""
        output_data = {}
        for link, result in classifications.items():
            output_data[link] = {
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

async def main():
    """Main function for testing"""
    # Example usage
    classifier = LinkClassifier()

    # Test with a simple example
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

if __name__ == "__main__":
    asyncio.run(main())
