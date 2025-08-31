"""
Tests for the build_search_docs.py script.
"""
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, LinkData, ClassificationResult
from scripts.build_search_docs import (
    extract_title_from_url, create_search_documents, validate_docs, write_search_data
)


@pytest.fixture
def db_session():
    """Creates a new database session for a test."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_extract_title_from_url():
    """Test URL title extraction."""
    assert "how slow is select | vettabase.com" in extract_title_from_url("https://vettabase.com/blog/how-slow-is-select/")
    assert extract_title_from_url("https://example.com/") == "example.com"
    assert extract_title_from_url("https://www.example.com/") == "example.com"


def test_create_search_documents(db_session):
    """Test the creation of search documents from database objects."""
    link1 = LinkData(
        link="http://example.com/1",
        status="classified",
        classification=ClassificationResult(
            category="Tech",
            subcategory="Programming",
            tags=["python"],
            summary="A summary"
        )
    )
    link2 = LinkData(link="http://example.com/2", status="Success") # No classification
    db_session.add_all([link1, link2])
    db_session.commit()

    links = db_session.query(LinkData).all()
    docs = create_search_documents(links)

    assert len(docs) == 1
    doc = docs[0]
    assert doc['url'] == "http://example.com/1"
    assert doc['category'] == "Tech"
    assert "python" in doc['tags']


def test_validate_docs():
    """Test document validation."""
    valid_docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test",
            "summary": "Test summary",
            "tags": ["tag1", "tag2"]
        }
    ]
    assert validate_docs(valid_docs) is True

    invalid_docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test"
        }
    ]
    assert validate_docs(invalid_docs) is False

    assert validate_docs([]) is False


def test_write_search_data(tmp_path):
    """Test writing search data to a JavaScript file."""
    docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test Article",
            "summary": "A test article",
            "tags": ["test"]
        }
    ]
    output_path = tmp_path / "search-data.js"
    write_search_data(docs, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding='utf-8')
    assert content.startswith("window.SEARCH_DATA = ")
    assert "test1" in content
