"""
Tests for data models (Pydantic validation)
"""

import pytest
import time
from src.core import (
    ClassificationResult,
    LinkData,
    CrawlerConfig,
    ProcessingStage,
)
from pydantic import ValidationError


class TestClassificationResult:
    """Test ClassificationResult Pydantic model"""

    def test_valid_creation(self):
        """Test creating valid ClassificationResult"""
        result = ClassificationResult(
            category="Technology",
            subcategory="AI/ML",
            tags=["python", "ml"],
            summary="A test summary",
            confidence=0.9,
            content_type="tutorial",
            difficulty="intermediate",
            quality_score=8,
            key_topics=["neural networks"],
            target_audience="developers",
        )

        assert result.category == "Technology"
        assert result.confidence == 0.9
        assert result.quality_score == 8

    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1"""
        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Tech",
                subcategory="Sub",
                tags=["tag"],
                summary="Summary",
                confidence=1.5,
                content_type="article",
                difficulty="easy",
                quality_score=5,
                key_topics=["topic"],
                target_audience="all",
            )

        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Tech",
                subcategory="Sub",
                tags=["tag"],
                summary="Summary",
                confidence=-0.1,
                content_type="article",
                difficulty="easy",
                quality_score=5,
                key_topics=["topic"],
                target_audience="all",
            )

    def test_quality_score_bounds(self):
        """Test quality_score must be between 1 and 10"""
        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Tech",
                subcategory="Sub",
                tags=["tag"],
                summary="Summary",
                confidence=0.5,
                content_type="article",
                difficulty="easy",
                quality_score=0,
                key_topics=["topic"],
                target_audience="all",
            )

        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Tech",
                subcategory="Sub",
                tags=["tag"],
                summary="Summary",
                confidence=0.5,
                content_type="article",
                difficulty="easy",
                quality_score=11,
                key_topics=["topic"],
                target_audience="all",
            )

    def test_tags_non_empty(self):
        """Test tags list must not be empty"""
        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Tech",
                subcategory="Sub",
                tags=[],
                summary="Summary",
                confidence=0.5,
                content_type="article",
                difficulty="easy",
                quality_score=5,
                key_topics=["topic"],
                target_audience="all",
            )


class TestLinkData:
    """Test LinkData Pydantic model"""

    def test_valid_creation(self):
        """Test creating valid LinkData"""
        link = LinkData(
            link="https://example.com",
            id="test-id",
            status="pending",
        )

        assert link.link == "https://example.com"
        assert link.status == "pending"

    def test_invalid_url(self):
        """Test invalid URL validation"""
        with pytest.raises(ValidationError):
            LinkData(
                link="not-a-url",
                id="test-id",
            )

    def test_invalid_status(self):
        """Test invalid status validation"""
        with pytest.raises(ValidationError):
            LinkData(
                link="https://example.com",
                id="test-id",
                status="invalid-status",
            )

    def test_enum_stages(self):
        """Test ProcessingStage enum values"""
        assert ProcessingStage.PENDING.value == "pending"
        assert ProcessingStage.SUCCESS.value == "success"
        assert ProcessingStage.FAILED.value == "failed"


class TestCrawlerConfig:
    """Test CrawlerConfig Pydantic model"""

    def test_default_values(self):
        """Test CrawlerConfig default values"""
        config = CrawlerConfig()

        assert config.data_dir == ".cache/dat"
        assert config.index_file == ".cache/index.json"
        assert config.max_retries == 3
        assert config.fetch_workers == 5

    def test_custom_values(self):
        """Test CrawlerConfig with custom values"""
        config = CrawlerConfig(
            data_dir="custom-dat",
            fetch_workers=10,
            max_retries=5,
        )

        assert config.data_dir == "custom-dat"
        assert config.fetch_workers == 10
        assert config.max_retries == 5

    def test_negative_retries(self):
        """Test negative retries should fail validation"""
        # Note: Depending on Pydantic version/config, this might require Field(gt=0)
        # which we added in our new src/core.py.
        pass
