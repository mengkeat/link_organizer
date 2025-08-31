"""
Tests for the ClassificationService.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, LinkData
from src.classification_service import ClassificationService
from src.models import ClassificationResult


@pytest.fixture
def db_session():
    """Creates a new database session for a test."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class MockLLMProvider:
    """A mock LLM provider for testing."""
    def __init__(self, content):
        self.content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def generate(self, prompt, temperature, max_tokens):
        return type('obj', (object,), {
            'content': self.content
        })()


@pytest.fixture
def classification_service():
    """Returns a ClassificationService with a mock LLM provider."""
    return ClassificationService(llm_provider=MockLLMProvider(
        '{"category": "AI/ML", "subcategory": "Deep Learning", "tags": ["neural networks", "tensorflow"], "summary": "A guide to deep learning.", "confidence": 0.9, "content_type": "tutorial", "difficulty": "intermediate", "quality_score": 8, "key_topics": ["deep learning"], "target_audience": "students"}'
    ))


def test_get_classification_prompt(classification_service):
    """Test classification prompt generation"""
    prompt = classification_service.get_classification_prompt(
        "https://example.com",
        "Test Title",
        "Test content"
    )

    assert "https://example.com" in prompt
    assert "Test Title" in prompt
    assert "Test content" in prompt
    assert "category" in prompt.lower()
    assert "json" in prompt.lower()


def test_parse_llm_response_valid_json(classification_service):
    """Test parsing valid JSON response"""
    json_response = '''
    {
        "category": "Technology",
        "tags": ["python", "ml"],
        "confidence": 0.9
    }
    '''

    result = classification_service.parse_llm_response(json_response)

    assert result["category"] == "Technology"
    assert result["tags"] == ["python", "ml"]
    assert result["confidence"] == 0.9


def test_parse_llm_response_json_with_text(classification_service):
    """Test parsing JSON response with surrounding text"""
    response_with_text = '''
    Here's the classification:
    {
        "category": "Technology",
        "tags": ["python"]
    }
    Hope this helps!
    '''

    result = classification_service.parse_llm_response(response_with_text)

    assert result["category"] == "Technology"
    assert result["tags"] == ["python"]


def test_parse_llm_response_text_fallback(classification_service):
    """Test fallback text parsing for non-JSON responses"""
    text_response = "This is a general article about technology and web development."

    result = classification_service.parse_text_response(text_response)

    assert result["category"] == "Technology"
    assert result["content_type"] == "article"
    assert result["confidence"] == 0.5


@pytest.mark.asyncio
async def test_classify_pending_links(db_session, classification_service):
    """Test that pending links are classified correctly."""
    # 1. Set up the test data
    link1 = LinkData(link="http://example.com/page1", status="Success", content="Some content")
    link2 = LinkData(link="http://example.com/page2", status="classified", content="Some other content")
    link3 = LinkData(link="http://example.com/page3", status="Success", content="More content")
    db_session.add_all([link1, link2, link3])
    db_session.commit()

    # 2. Run the classification service
    await classification_service.classify_pending_links(session=db_session)

    # 3. Assert the results
    assert link1.status == "classified"
    assert link1.classification is not None
    assert link1.classification.category == "AI/ML"

    assert link2.classification is None # Should not have been processed

    assert link3.status == "classified"
    assert link3.classification is not None
    assert link3.classification.category == "AI/ML"
