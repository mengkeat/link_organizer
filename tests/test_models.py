"""
Tests for data models (Pydantic validation)
"""

import pytest
import time
from src.models import (
    ClassificationResult,
    LinkData,
    CrawlerConfig,
    ProcessingStage,
    WorkerStatus,
    QueueStats,
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
        """Test tags must be non-empty list"""
        with pytest.raises(ValidationError) as exc_info:
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

        assert "tags must be a non-empty list" in str(exc_info.value)

    def test_to_dict(self):
        """Test to_dict returns proper dictionary"""
        result = ClassificationResult(
            category="Technology",
            subcategory="AI/ML",
            tags=["python"],
            summary="Summary",
            confidence=0.9,
            content_type="tutorial",
            difficulty="intermediate",
            quality_score=8,
            key_topics=["ml"],
            target_audience="developers",
        )

        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["category"] == "Technology"
        assert d["tags"] == ["python"]
        assert d["confidence"] == 0.9

    def test_edge_confidence_values(self):
        """Test edge values for confidence (0.0 and 1.0)"""
        result_zero = ClassificationResult(
            category="Tech",
            subcategory="Sub",
            tags=["tag"],
            summary="Summary",
            confidence=0.0,
            content_type="article",
            difficulty="easy",
            quality_score=5,
            key_topics=["topic"],
            target_audience="all",
        )
        assert result_zero.confidence == 0.0

        result_one = ClassificationResult(
            category="Tech",
            subcategory="Sub",
            tags=["tag"],
            summary="Summary",
            confidence=1.0,
            content_type="article",
            difficulty="easy",
            quality_score=5,
            key_topics=["topic"],
            target_audience="all",
        )
        assert result_one.confidence == 1.0

    def test_edge_quality_score_values(self):
        """Test edge values for quality_score (1 and 10)"""
        result_min = ClassificationResult(
            category="Tech",
            subcategory="Sub",
            tags=["tag"],
            summary="Summary",
            confidence=0.5,
            content_type="article",
            difficulty="easy",
            quality_score=1,
            key_topics=["topic"],
            target_audience="all",
        )
        assert result_min.quality_score == 1

        result_max = ClassificationResult(
            category="Tech",
            subcategory="Sub",
            tags=["tag"],
            summary="Summary",
            confidence=0.5,
            content_type="article",
            difficulty="easy",
            quality_score=10,
            key_topics=["topic"],
            target_audience="all",
        )
        assert result_max.quality_score == 10


class TestLinkData:
    """Test LinkData Pydantic model"""

    def test_valid_creation(self):
        """Test creating valid LinkData"""
        link_data = LinkData(
            link="https://example.com",
            id="abc123",
        )

        assert link_data.link == "https://example.com"
        assert link_data.id == "abc123"
        assert link_data.status == "pending"
        assert link_data.filename is None
        assert link_data.content is None
        assert link_data.classification is None

    def test_valid_url_formats(self):
        """Test various valid URL formats"""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path/to/page",
            "https://example.com:8080/path",
            "http://localhost:3000",
            "https://sub.domain.example.com",
            "https://example.com/path?query=value",
        ]

        for url in valid_urls:
            link_data = LinkData(link=url, id="test")
            assert link_data.link == url

    def test_invalid_url_formats(self):
        """Test invalid URL formats raise ValidationError"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "example.com",
            "//example.com",
            "",
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError):
                LinkData(link=url, id="test")

    def test_valid_status_values(self):
        """Test valid status values"""
        valid_statuses = [
            "pending",
            "fetching",
            "fetch_complete",
            "classifying",
            "success",
            "failed",
        ]

        for status in valid_statuses:
            link_data = LinkData(
                link="https://example.com",
                id="test",
                status=status,
            )
            assert link_data.status == status

    def test_invalid_status_value(self):
        """Test invalid status raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            LinkData(
                link="https://example.com",
                id="test",
                status="invalid_status",
            )

        assert "status must be one of" in str(exc_info.value)

    def test_with_classification(self):
        """Test LinkData with nested ClassificationResult"""
        classification = ClassificationResult(
            category="Technology",
            subcategory="AI/ML",
            tags=["python"],
            summary="Summary",
            confidence=0.9,
            content_type="tutorial",
            difficulty="intermediate",
            quality_score=8,
            key_topics=["ml"],
            target_audience="developers",
        )

        link_data = LinkData(
            link="https://example.com",
            id="test",
            classification=classification,
        )

        assert link_data.classification is not None
        assert link_data.classification.category == "Technology"

    def test_to_dict_without_content(self):
        """Test to_dict excludes content by default"""
        link_data = LinkData(
            link="https://example.com",
            id="test",
            content="Some content",
        )

        d = link_data.to_dict()

        assert "content" not in d
        assert d["link"] == "https://example.com"

    def test_to_dict_with_content(self):
        """Test to_dict includes content when requested"""
        link_data = LinkData(
            link="https://example.com",
            id="test",
            content="Some content",
        )

        d = link_data.to_dict(include_content=True)

        assert d["content"] == "Some content"

    def test_to_dict_with_classification(self):
        """Test to_dict includes classification when present"""
        classification = ClassificationResult(
            category="Technology",
            subcategory="AI/ML",
            tags=["python"],
            summary="Summary",
            confidence=0.9,
            content_type="tutorial",
            difficulty="intermediate",
            quality_score=8,
            key_topics=["ml"],
            target_audience="developers",
        )

        link_data = LinkData(
            link="https://example.com",
            id="test",
            classification=classification,
        )

        d = link_data.to_dict()

        assert "classification" in d
        assert d["classification"]["category"] == "Technology"

    def test_to_dict_without_classification(self):
        """Test to_dict when no classification"""
        link_data = LinkData(
            link="https://example.com",
            id="test",
        )

        d = link_data.to_dict()

        assert d.get("classification") is None

    def test_validate_assignment(self):
        """Test that assignment validation is enabled"""
        link_data = LinkData(
            link="https://example.com",
            id="test",
        )

        with pytest.raises(ValidationError):
            link_data.status = "invalid"


class TestCrawlerConfig:
    """Test CrawlerConfig Pydantic model"""

    def test_default_values(self):
        """Test default configuration values"""
        config = CrawlerConfig()

        assert config.data_dir == "dat"
        assert config.index_file == "index.json"
        assert config.classifications_file == "classifications.json"
        assert config.max_retries == 3
        assert config.classification_workers == 5
        assert config.fetch_workers == 5
        assert config.request_delay == 1.0
        assert config.enable_tui is False

    def test_custom_values(self):
        """Test custom configuration values"""
        config = CrawlerConfig(
            data_dir="custom_data",
            max_retries=5,
            classification_workers=10,
            fetch_workers=8,
            request_delay=2.5,
            enable_tui=True,
        )

        assert config.data_dir == "custom_data"
        assert config.max_retries == 5
        assert config.classification_workers == 10
        assert config.fetch_workers == 8
        assert config.request_delay == 2.5
        assert config.enable_tui is True

    def test_max_retries_positive(self):
        """Test max_retries must be positive"""
        with pytest.raises(ValidationError):
            CrawlerConfig(max_retries=0)

        with pytest.raises(ValidationError):
            CrawlerConfig(max_retries=-1)

    def test_workers_positive(self):
        """Test workers must be positive"""
        with pytest.raises(ValidationError):
            CrawlerConfig(classification_workers=0)

        with pytest.raises(ValidationError):
            CrawlerConfig(fetch_workers=-1)

    def test_request_delay_non_negative(self):
        """Test request_delay must be non-negative"""
        config = CrawlerConfig(request_delay=0.0)
        assert config.request_delay == 0.0

        with pytest.raises(ValidationError):
            CrawlerConfig(request_delay=-0.1)


class TestProcessingStage:
    """Test ProcessingStage enum"""

    def test_enum_values(self):
        """Test all processing stages have correct values"""
        assert ProcessingStage.PENDING.value == "pending"
        assert ProcessingStage.FETCHING.value == "fetching"
        assert ProcessingStage.FETCH_COMPLETE.value == "fetch_complete"
        assert ProcessingStage.CLASSIFYING.value == "classifying"
        assert ProcessingStage.SUCCESS.value == "success"
        assert ProcessingStage.FAILED.value == "failed"

    def test_all_stages_defined(self):
        """Test all expected stages are defined"""
        stages = [stage.value for stage in ProcessingStage]

        assert "pending" in stages
        assert "fetching" in stages
        assert "fetch_complete" in stages
        assert "classifying" in stages
        assert "success" in stages
        assert "failed" in stages


class TestWorkerStatus:
    """Test WorkerStatus Pydantic model"""

    def test_creation(self):
        """Test creating WorkerStatus"""
        status = WorkerStatus(
            worker_id="worker-1",
            worker_type="fetch",
        )

        assert status.worker_id == "worker-1"
        assert status.worker_type == "fetch"
        assert status.status == "idle"
        assert status.current_task is None
        assert status.last_update > 0

    def test_with_task(self):
        """Test WorkerStatus with current task"""
        status = WorkerStatus(
            worker_id="worker-1",
            worker_type="classification",
            status="working",
            current_task="https://example.com",
        )

        assert status.status == "working"
        assert status.current_task == "https://example.com"


class TestQueueStats:
    """Test QueueStats Pydantic model"""

    def test_default_values(self):
        """Test default queue stats"""
        stats = QueueStats()

        assert stats.fetch_queue_size == 0
        assert stats.classification_queue_size == 0
        assert stats.completed_count == 0
        assert stats.failed_count == 0
        assert stats.total_count == 0

    def test_completion_percentage_zero_total(self):
        """Test completion percentage when total is zero"""
        stats = QueueStats(total_count=0)

        assert stats.completion_percentage == 0.0

    def test_completion_percentage_calculation(self):
        """Test completion percentage calculation"""
        stats = QueueStats(
            total_count=100,
            completed_count=50,
            failed_count=10,
        )

        assert stats.completion_percentage == 60.0

    def test_completion_percentage_all_completed(self):
        """Test completion percentage at 100%"""
        stats = QueueStats(
            total_count=10,
            completed_count=10,
            failed_count=0,
        )

        assert stats.completion_percentage == 100.0

    def test_elapsed_time(self):
        """Test elapsed time calculation"""
        start = time.time()
        stats = QueueStats(start_time=start)

        time.sleep(0.1)

        assert stats.elapsed_time >= 0.1
        assert stats.elapsed_time < 1.0
