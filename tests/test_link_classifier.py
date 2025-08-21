"""
Tests for LinkClassifier
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from link_classifier import LinkClassifier, ClassificationResult
from src.llm.base import LLMResponse
from src.llm.litellm_provider import LiteLLMProvider
from src.llm.openrouter_provider import OpenRouterProvider


class TestClassificationResult:
    """Test ClassificationResult dataclass"""

    def test_classification_result_creation(self):
        """Test creating ClassificationResult"""
        result = ClassificationResult(
            category="Technology",
            subcategory="AI/ML",
            tags=["python", "machine learning"],
            summary="A guide to ML",
            confidence=0.9,
            content_type="tutorial",
            difficulty="intermediate",
            quality_score=8,
            key_topics=["neural networks", "deep learning"],
            target_audience="developers"
        )

        assert result.category == "Technology"
        assert result.subcategory == "AI/ML"
        assert result.tags == ["python", "machine learning"]
        assert result.summary == "A guide to ML"
        assert result.confidence == 0.9
        assert result.content_type == "tutorial"
        assert result.difficulty == "intermediate"
        assert result.quality_score == 8
        assert result.key_topics == ["neural networks", "deep learning"]
        assert result.target_audience == "developers"


class TestLinkClassifier:
    """Test LinkClassifier"""

    def test_initialization_default(self):
        """Test initialization with default provider"""
        with patch('src.llm.factory.LLMProviderFactory.from_env') as mock_factory:
            mock_provider = MagicMock()
            mock_factory.return_value = mock_provider

            classifier = LinkClassifier()

            mock_factory.assert_called_once()
            assert classifier.llm_provider == mock_provider

    def test_initialization_with_provider(self):
        """Test initialization with custom provider"""
        mock_provider = MagicMock()
        classifier = LinkClassifier(llm_provider=mock_provider)

        assert classifier.llm_provider == mock_provider

    def test_categories_and_types(self):
        """Test that categories and content types are defined"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        assert len(classifier.categories) > 0
        assert len(classifier.content_types) > 0
        assert "Technology" in classifier.categories
        assert "tutorial" in classifier.content_types

    def test_get_classification_prompt(self):
        """Test classification prompt generation"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        prompt = classifier.get_classification_prompt(
            "https://example.com",
            "Test Title",
            "Test content"
        )

        assert "https://example.com" in prompt
        assert "Test Title" in prompt
        assert "Test content" in prompt
        assert "category" in prompt.lower()
        assert "json" in prompt.lower()

    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        json_response = '''
        {
            "category": "Technology",
            "subcategory": "AI/ML",
            "tags": ["python", "ml"],
            "summary": "Test summary",
            "confidence": 0.9,
            "content_type": "tutorial",
            "difficulty": "intermediate",
            "quality_score": 8,
            "key_topics": ["neural networks"],
            "target_audience": "developers"
        }
        '''

        result = classifier.parse_llm_response(json_response)

        assert result["category"] == "Technology"
        assert result["tags"] == ["python", "ml"]
        assert result["confidence"] == 0.9

    def test_parse_llm_response_json_with_text(self):
        """Test parsing JSON response with surrounding text"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        response_with_text = '''
        Here's the classification:
        {
            "category": "Technology",
            "subcategory": "Programming",
            "tags": ["python"],
            "summary": "Test summary",
            "confidence": 0.8,
            "content_type": "guide",
            "difficulty": "beginner",
            "quality_score": 7,
            "key_topics": ["coding"],
            "target_audience": "students"
        }
        Hope this helps!
        '''

        result = classifier.parse_llm_response(response_with_text)

        assert result["category"] == "Technology"
        assert result["tags"] == ["python"]

    def test_parse_llm_response_text_fallback(self):
        """Test fallback text parsing for non-JSON responses"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        text_response = "This is a general article about technology and web development."

        result = classifier.parse_text_response(text_response)

        assert result["category"] == "Technology"
        assert result["content_type"] == "article"
        assert result["confidence"] == 0.5

    def test_parse_llm_response_invalid_json(self):
        """Test parsing invalid JSON response falls back to text parsing"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        invalid_json = '{"category": "Technology", "invalid": json}'

        result = classifier.parse_llm_response(invalid_json)

        # Should fall back to text parsing
        assert result["category"] == "Technology"
        assert result["content_type"] == "article"

    def test_get_fallback_classification(self):
        """Test fallback classification generation"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        fallback = classifier.get_fallback_classification(
            "https://example.com",
            "Test Title",
            "Test content"
        )

        assert isinstance(fallback, ClassificationResult)
        assert fallback.category == "Technology"
        assert fallback.confidence == 0.3

    @patch('builtins.open')
    def test_extract_pdf_text(self, mock_open):
        """Test PDF text extraction"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        # Mock PDF reader
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content"
        mock_pdf.pages = [mock_page]

        with patch('PyPDF2.PdfReader', return_value=mock_pdf):
            result = classifier.extract_pdf_text(Path("test.pdf"))

        assert result == "PDF content\n"

    def test_extract_content_from_markdown(self, tmp_path):
        """Test markdown content extraction"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        # Create a temporary markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Content\nThis is markdown content.")

        result = classifier.extract_content_from_file(md_file)

        assert "# Test Content" in result
        assert "This is markdown content." in result

    def test_extract_content_from_unsupported_file(self, tmp_path):
        """Test handling of unsupported file types"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Text content")

        result = classifier.extract_content_from_file(txt_file)

        assert "Unsupported file type: .txt" in result

    def test_hash_link(self):
        """Test link hashing"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        hash1 = classifier.hash_link("https://example.com")
        hash2 = classifier.hash_link("https://example.com")
        hash3 = classifier.hash_link("https://different.com")

        assert hash1 == hash2  # Same input should give same hash
        assert hash1 != hash3  # Different input should give different hash
        assert len(hash1) == 64  # SHA256 hex length

    async def test_classify_content_success(self):
        """Test successful content classification"""
        # Mock provider
        mock_provider = MagicMock()
        mock_response = LLMResponse(
            content='{"category": "Technology", "subcategory": "AI/ML", "tags": ["python"], "summary": "Test", "confidence": 0.9, "content_type": "tutorial", "difficulty": "intermediate", "quality_score": 8, "key_topics": ["ml"], "target_audience": "developers"}',
            model="test-model"
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        classifier = LinkClassifier(llm_provider=mock_provider)

        result = await classifier.classify_content(
            "https://example.com",
            "Test Title",
            "Test content"
        )

        assert isinstance(result, ClassificationResult)
        assert result.category == "Technology"
        assert result.subcategory == "AI/ML"
        assert result.tags == ["python"]

    async def test_classify_content_failure(self):
        """Test content classification failure with fallback"""
        # Mock provider that raises an exception
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("API Error"))

        classifier = LinkClassifier(llm_provider=mock_provider)

        result = await classifier.classify_content(
            "https://example.com",
            "Test Title",
            "Test content"
        )

        # Should return fallback classification
        assert isinstance(result, ClassificationResult)
        assert result.confidence == 0.3

    def test_save_classifications(self, tmp_path):
        """Test saving classifications to file"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        classifications = {
            "https://example.com": ClassificationResult(
                category="Technology",
                subcategory="AI/ML",
                tags=["python"],
                summary="Test summary",
                confidence=0.9,
                content_type="tutorial",
                difficulty="intermediate",
                quality_score=8,
                key_topics=["ml"],
                target_audience="developers"
            )
        }

        output_file = tmp_path / "test_classifications.json"
        classifier.save_classifications(classifications, output_file)

        assert output_file.exists()

        # Verify content
        saved_data = json.loads(output_file.read_text())
        assert "https://example.com" in saved_data
        assert saved_data["https://example.com"]["category"] == "Technology"
        assert saved_data["https://example.com"]["tags"] == ["python"]

    def test_classify_existing_links_file_not_found(self, tmp_path):
        """Test classify_existing_links with missing index file"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        result = asyncio.run(classifier.classify_existing_links(tmp_path / "nonexistent.json"))

        assert result == {}

    def test_classify_existing_links_empty_index(self, tmp_path):
        """Test classify_existing_links with empty index file"""
        with patch('src.llm.factory.LLMProviderFactory.from_env'):
            classifier = LinkClassifier()

        index_file = tmp_path / "empty_index.json"
        index_file.write_text("[]")

        result = asyncio.run(classifier.classify_existing_links(index_file))

        assert result == {}


class TestLinkClassifierIntegration:
    """Integration tests for LinkClassifier with different providers"""

    async def test_with_litellm_provider(self):
        """Test LinkClassifier with LiteLLM provider"""
        mock_provider = LiteLLMProvider("test_key", "gpt-4")

        # Mock the actual generation
        with patch.object(mock_provider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = LLMResponse(
                content='{"category": "Technology", "subcategory": "Programming", "tags": ["python"], "summary": "Python guide", "confidence": 0.8, "content_type": "tutorial", "difficulty": "beginner", "quality_score": 7, "key_topics": ["python"], "target_audience": "beginners"}',
                model="gpt-4"
            )

            classifier = LinkClassifier(llm_provider=mock_provider)

            result = await classifier.classify_content(
                "https://example.com/python",
                "Python Tutorial",
                "Learn Python programming"
            )

            assert result.category == "Technology"
            assert result.subcategory == "Programming"
            mock_generate.assert_called_once()

    async def test_with_openrouter_provider(self):
        """Test LinkClassifier with OpenRouter provider"""
        mock_provider = OpenRouterProvider("test_key", "gpt-4")

        # Mock the actual generation
        with patch.object(mock_provider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = LLMResponse(
                content='{"category": "AI/ML", "subcategory": "Machine Learning", "tags": ["ml", "ai"], "summary": "ML guide", "confidence": 0.9, "content_type": "guide", "difficulty": "advanced", "quality_score": 9, "key_topics": ["machine learning"], "target_audience": "experts"}',
                model="openrouter/gpt-4"
            )

            classifier = LinkClassifier(llm_provider=mock_provider)

            result = await classifier.classify_content(
                "https://example.com/ml",
                "Machine Learning Guide",
                "Advanced ML concepts"
            )

            assert result.category == "AI/ML"
            assert result.difficulty == "advanced"
            mock_generate.assert_called_once()
