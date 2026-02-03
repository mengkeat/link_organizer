"""
Tests for incremental crawler functionality
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from src.incremental_crawler import run_incremental_crawl
from src.link_index import LinkIndex, IndexEntry
from src.models import ClassificationResult, LinkData, CrawlerConfig
from src.filename_generator import FilenameGenerator
from src.content_processor import ContentProcessor
from src.crawler_utils import CrawlerUtils

from .fixtures import (
    MockAsyncWebCrawler,
    MockClassificationService,
    MockCrawlResult,
    create_mock_classification_result,
    create_mock_index_entry,
    create_temp_index,
    create_temp_index_with_links,
    SAMPLE_URLS,
    SAMPLE_MARKDOWN_CONTENT,
    SAMPLE_CLASSIFICATION_JSON,
)


class TestFilenameGenerator:
    """Test FilenameGenerator utility class"""

    def test_generate_readable_filename_basic(self):
        """Test basic filename generation from URL"""
        url = "https://example.com/blog/my-article"
        result = FilenameGenerator.generate_readable_filename(url, "md")
        
        assert result.endswith(".md")
        assert "example" in result
        assert "-" in result

    def test_generate_readable_filename_arxiv(self):
        """Test filename generation for arxiv URLs"""
        url = "https://arxiv.org/abs/2105.00613"
        result = FilenameGenerator.generate_readable_filename(url, "pdf")
        
        assert result.endswith(".pdf")
        assert "arxiv" in result
        assert "2105" in result

    def test_generate_readable_filename_github(self):
        """Test filename generation for GitHub URLs"""
        url = "https://github.com/user/my-repo"
        result = FilenameGenerator.generate_readable_filename(url, "md")
        
        assert result.endswith(".md")
        assert "github" in result
        assert "user" in result or "my-repo" in result

    def test_generate_readable_filename_max_length(self):
        """Test filename respects max length"""
        url = "https://example.com/very/long/path/with/many/segments/that/should/be/truncated"
        result = FilenameGenerator.generate_readable_filename(url, "md", max_length=30)
        
        base_name = result.rsplit('.', 1)[0]
        assert len(base_name) <= 30

    def test_generate_readable_filename_empty_path(self):
        """Test filename generation for URL with empty path"""
        url = "https://example.com/"
        result = FilenameGenerator.generate_readable_filename(url, "md")
        
        assert result.endswith(".md")
        assert len(result) > 3

    def test_sanitize_filename(self):
        """Test filename sanitization removes invalid characters"""
        filename = 'test<>:"/\\|?*file.md'
        result = FilenameGenerator.sanitize_filename(filename)
        
        for char in '<>:"/\\|?*':
            assert char not in result

    def test_make_unique_filename_no_conflict(self):
        """Test unique filename when no conflict exists"""
        filename = "test-file.md"
        existing = {"other-file.md", "another-file.md"}
        
        result = FilenameGenerator.make_unique_filename(filename, existing)
        assert result == filename

    def test_make_unique_filename_with_conflict(self):
        """Test unique filename when conflict exists"""
        filename = "test-file.md"
        existing = {"test-file.md", "other-file.md"}
        
        result = FilenameGenerator.make_unique_filename(filename, existing)
        assert result == "test-file-1.md"

    def test_make_unique_filename_multiple_conflicts(self):
        """Test unique filename with multiple conflicts"""
        filename = "test-file.md"
        existing = {"test-file.md", "test-file-1.md", "test-file-2.md"}
        
        result = FilenameGenerator.make_unique_filename(filename, existing)
        assert result == "test-file-3.md"


class TestLinkIndex:
    """Test LinkIndex class"""

    def test_create_empty_index(self, tmp_path):
        """Test creating empty index"""
        index = create_temp_index(tmp_path)
        
        assert len(index.get_all()) == 0
        assert index.get_existing_links() == set()

    def test_add_entry(self, tmp_path):
        """Test adding entry to index"""
        index = create_temp_index(tmp_path)
        entry = create_mock_index_entry(link="https://example.com/new")
        
        index.add(entry)
        
        assert index.get("https://example.com/new") is not None
        assert len(index.get_all()) == 1

    def test_get_successful_links(self, tmp_path):
        """Test getting successful links"""
        entries = [
            create_mock_index_entry(link="https://example.com/1", status="Success"),
            create_mock_index_entry(link="https://example.com/2", status="Failed: Error"),
            create_mock_index_entry(link="https://example.com/3", status="Success"),
        ]
        index = create_temp_index(tmp_path, entries)
        
        successful = index.get_successful_links()
        
        assert len(successful) == 2
        assert "https://example.com/1" in successful
        assert "https://example.com/3" in successful

    def test_get_failed_links(self, tmp_path):
        """Test getting failed links"""
        entries = [
            create_mock_index_entry(link="https://example.com/1", status="Success"),
            create_mock_index_entry(link="https://example.com/2", status="Failed: Error"),
            create_mock_index_entry(link="https://example.com/3", status="Failed: Timeout"),
        ]
        index = create_temp_index(tmp_path, entries)
        
        failed = index.get_failed_links()
        
        assert len(failed) == 2
        assert "https://example.com/2" in failed
        assert "https://example.com/3" in failed

    def test_find_new_links(self, tmp_path):
        """Test finding new links not in index"""
        entries = [
            create_mock_index_entry(link="https://example.com/existing"),
        ]
        index = create_temp_index(tmp_path, entries)
        
        all_links = [
            "https://example.com/existing",
            "https://example.com/new1",
            "https://example.com/new2",
        ]
        
        new_links = index.find_new_links(all_links)
        
        assert len(new_links) == 2
        assert "https://example.com/new1" in new_links
        assert "https://example.com/new2" in new_links

    def test_save_and_load(self, tmp_path):
        """Test saving and loading index"""
        index = create_temp_index(tmp_path)
        entry = create_mock_index_entry(link="https://example.com/test")
        index.add(entry)
        index.save()
        
        # Load fresh index
        reloaded_index = LinkIndex(tmp_path / "test_index.json")
        
        assert len(reloaded_index.get_all()) == 1
        assert reloaded_index.get("https://example.com/test") is not None

    def test_get_stats(self, tmp_path):
        """Test getting index statistics"""
        entries = [
            create_mock_index_entry(link="https://example.com/1", status="Success"),
            create_mock_index_entry(link="https://example.com/2", status="Failed: Error"),
            create_mock_index_entry(link="https://example.com/3", status="pending"),
        ]
        index = create_temp_index(tmp_path, entries)
        
        stats = index.get_stats()
        
        assert stats["total"] == 3
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1


class TestCrawlerUtils:
    """Test CrawlerUtils class"""

    def test_is_pdf_url(self):
        """Test PDF URL detection"""
        assert CrawlerUtils.is_pdf("https://arxiv.org/pdf/2105.00613.pdf") is True
        assert CrawlerUtils.is_pdf("https://example.com/document.PDF") is True
        assert CrawlerUtils.is_pdf("https://example.com/article") is False
        assert CrawlerUtils.is_pdf("https://example.com/article.html") is False

    @patch('requests.get')
    def test_download_pdf_success(self, mock_get):
        """Test successful PDF download"""
        mock_response = MagicMock()
        mock_response.content = b"PDF content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        content, typ = CrawlerUtils._download_pdf("https://example.com/doc.pdf")
        
        assert content == b"PDF content"
        assert typ == "pdf"

    @patch('requests.get')
    def test_download_pdf_failure(self, mock_get):
        """Test PDF download failure"""
        mock_get.side_effect = Exception("Network error")
        
        content, typ = CrawlerUtils._download_pdf("https://example.com/doc.pdf")
        
        assert content is None
        assert typ is None

    @pytest.mark.asyncio
    async def test_fetch_html_content_success(self):
        """Test successful HTML content fetch"""
        mock_crawler = MockAsyncWebCrawler({
            "https://example.com/article": MockCrawlResult(
                success=True,
                markdown="# Article\n\nContent here",
                screenshot="base64screenshot"
            )
        })
        
        async with mock_crawler as crawler:
            content, typ, screenshot = await CrawlerUtils._fetch_html_content(
                crawler, "https://example.com/article"
            )
        
        assert content == "# Article\n\nContent here"
        assert typ == "md"
        assert screenshot == "base64screenshot"

    @pytest.mark.asyncio
    async def test_fetch_html_content_failure(self):
        """Test HTML content fetch failure"""
        mock_crawler = MockAsyncWebCrawler({
            "https://example.com/fail": MockCrawlResult(success=False)
        })
        
        async with mock_crawler as crawler:
            content, typ, screenshot = await CrawlerUtils._fetch_html_content(
                crawler, "https://example.com/fail"
            )
        
        assert content is None
        assert typ is None
        assert screenshot is None


class TestContentProcessor:
    """Test ContentProcessor class"""

    def test_hash_link(self):
        """Test link hashing"""
        hash1 = ContentProcessor.hash_link("https://example.com")
        hash2 = ContentProcessor.hash_link("https://example.com")
        hash3 = ContentProcessor.hash_link("https://different.com")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64

    def test_generate_title_from_url(self):
        """Test title generation from URL"""
        title = ContentProcessor.generate_title_from_url("https://example.com/my-article")
        
        assert "My" in title or "Article" in title

    def test_extract_content_from_markdown_file(self, tmp_path):
        """Test extracting content from markdown file"""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nContent here")
        
        result = ContentProcessor.extract_content_from_file(md_file)
        
        assert "# Test" in result
        assert "Content here" in result

    def test_extract_content_unsupported_file(self, tmp_path):
        """Test extracting content from unsupported file type"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Text content")
        
        result = ContentProcessor.extract_content_from_file(txt_file)
        
        assert "Unsupported file type" in result


class TestRunIncrementalCrawl:
    """Test run_incremental_crawl function"""

    @pytest.mark.asyncio
    @patch('src.incremental_crawler.AsyncWebCrawler')
    @patch('src.incremental_crawler.ClassificationService')
    @patch('src.incremental_crawler.load_dotenv')
    async def test_crawl_empty_links(self, mock_dotenv, mock_classification_service, mock_crawler, tmp_path):
        """Test crawl with empty links list"""
        index = create_temp_index(tmp_path)
        
        await run_incremental_crawl([], index, use_tui=False, workers=1)
        
        assert len(index.get_all()) == 0

    @pytest.mark.asyncio
    @patch('src.incremental_crawler.AsyncWebCrawler')
    @patch('src.incremental_crawler.ClassificationService')
    @patch('src.incremental_crawler.CrawlerUtils')
    @patch('src.incremental_crawler.load_dotenv')
    async def test_crawl_single_link_success(
        self, mock_dotenv, mock_crawler_utils, mock_classification_service, mock_crawler_class, tmp_path
    ):
        """Test successful crawl of a single link"""
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler_class.return_value = mock_crawler
        
        mock_crawler_utils.fetch_and_convert = AsyncMock(
            return_value=("# Test Content", "md", None)
        )
        
        mock_service = MagicMock()
        mock_service.classify_content = AsyncMock(
            return_value=create_mock_classification_result()
        )
        mock_classification_service.return_value = mock_service
        
        data_dir = tmp_path / "dat"
        data_dir.mkdir()
        
        index = create_temp_index(tmp_path)
        
        with patch.object(CrawlerConfig, '__init__', lambda self, **kwargs: None):
            with patch('src.incremental_crawler.CrawlerConfig') as mock_config:
                config_instance = MagicMock()
                config_instance.data_dir = str(data_dir)
                config_instance.fetch_workers = 1
                config_instance.classification_workers = 1
                config_instance.request_delay = 0
                config_instance.index_file = str(tmp_path / "test_index.json")
                config_instance.classifications_file = str(tmp_path / "classifications.json")
                mock_config.return_value = config_instance
                
                await run_incremental_crawl(
                    ["https://example.com/test"],
                    index,
                    use_tui=False,
                    workers=1
                )

    @pytest.mark.asyncio
    @patch('src.incremental_crawler.AsyncWebCrawler')
    @patch('src.incremental_crawler.ClassificationService')
    @patch('src.incremental_crawler.CrawlerUtils')
    @patch('src.incremental_crawler.load_dotenv')
    async def test_crawl_handles_fetch_failure(
        self, mock_dotenv, mock_crawler_utils, mock_classification_service, mock_crawler_class, tmp_path
    ):
        """Test crawl handles fetch failures gracefully"""
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler_class.return_value = mock_crawler
        
        mock_crawler_utils.fetch_and_convert = AsyncMock(
            return_value=(None, None, None)
        )
        
        mock_service = MagicMock()
        mock_classification_service.return_value = mock_service
        
        data_dir = tmp_path / "dat"
        data_dir.mkdir()
        
        index = create_temp_index(tmp_path)
        
        with patch('src.incremental_crawler.CrawlerConfig') as mock_config:
            config_instance = MagicMock()
            config_instance.data_dir = str(data_dir)
            config_instance.fetch_workers = 1
            config_instance.classification_workers = 1
            config_instance.request_delay = 0
            config_instance.index_file = str(tmp_path / "test_index.json")
            config_instance.classifications_file = str(tmp_path / "classifications.json")
            mock_config.return_value = config_instance
            
            await run_incremental_crawl(
                ["https://example.com/fail"],
                index,
                use_tui=False,
                workers=1
            )

    def test_incremental_skips_processed_links(self, tmp_path):
        """Test that incremental crawl logic skips already processed links"""
        existing_entries = [
            create_mock_index_entry(link="https://example.com/already-done", status="Success"),
        ]
        index = create_temp_index(tmp_path, existing_entries)
        
        all_links = [
            "https://example.com/already-done",
            "https://example.com/new-link",
        ]
        
        new_links = index.find_new_links(all_links)
        
        assert len(new_links) == 1
        assert "https://example.com/new-link" in new_links
        assert "https://example.com/already-done" not in new_links

    def test_retry_finds_failed_links(self, tmp_path):
        """Test that retry finds failed links"""
        entries = [
            create_mock_index_entry(link="https://example.com/success", status="Success"),
            create_mock_index_entry(link="https://example.com/failed1", status="Failed: Timeout"),
            create_mock_index_entry(link="https://example.com/failed2", status="Failed: No content"),
        ]
        index = create_temp_index(tmp_path, entries)
        
        retry_links = index.find_links_to_retry()
        
        assert len(retry_links) == 2
        assert "https://example.com/failed1" in retry_links
        assert "https://example.com/failed2" in retry_links


class TestClassificationServiceIntegration:
    """Test classification service integration with crawler"""

    @pytest.mark.asyncio
    async def test_mock_classification_service(self):
        """Test MockClassificationService works correctly"""
        service = MockClassificationService()
        
        result = await service.classify_content(
            "https://example.com/test",
            "Test Title",
            "Test content"
        )
        
        assert isinstance(result, ClassificationResult)
        assert result.category == "Technology"
        assert len(service.classify_calls) == 1

    @pytest.mark.asyncio
    async def test_mock_classification_with_custom_results(self):
        """Test MockClassificationService with custom results"""
        custom_result = create_mock_classification_result(
            category="AI/ML",
            tags=["machine-learning", "neural-networks"]
        )
        
        service = MockClassificationService({
            "https://example.com/ml": custom_result
        })
        
        result = await service.classify_content(
            "https://example.com/ml",
            "ML Article",
            "Machine learning content"
        )
        
        assert result.category == "AI/ML"
        assert "machine-learning" in result.tags


class TestIndexEntryCreation:
    """Test IndexEntry creation and serialization"""

    def test_index_entry_to_dict(self):
        """Test IndexEntry serialization"""
        entry = create_mock_index_entry()
        
        data = entry.to_dict()
        
        assert "link" in data
        assert "id" in data
        assert "status" in data
        assert "classification" in data

    def test_index_entry_from_dict(self):
        """Test IndexEntry deserialization"""
        data = {
            "link": "https://example.com/test",
            "id": "test123",
            "filename": "test123.md",
            "readable_filename": "example-test.md",
            "status": "Success",
            "crawled_at": "2024-01-01T12:00:00",
            "classification": SAMPLE_CLASSIFICATION_JSON
        }
        
        entry = IndexEntry.from_dict(data)
        
        assert entry.link == "https://example.com/test"
        assert entry.status == "Success"
        assert entry.classification["category"] == "Technology"

    def test_index_entry_with_screenshot(self):
        """Test IndexEntry with screenshot filename"""
        entry = IndexEntry(
            link="https://example.com/test",
            id="test123",
            filename="test123.md",
            status="Success",
            screenshot_filename="test123_screenshot.jpg"
        )
        
        data = entry.to_dict()
        
        assert data["screenshot_filename"] == "test123_screenshot.jpg"


class TestFilenameCollisionHandling:
    """Test filename collision handling in crawl process"""

    def test_existing_filenames_tracking(self, tmp_path):
        """Test that existing filenames are tracked from index"""
        entries = [
            create_mock_index_entry(
                link="https://example.com/1",
                readable_filename="example-1.md"
            ),
            create_mock_index_entry(
                link="https://example.com/2", 
                readable_filename="example-2.md"
            ),
        ]
        index = create_temp_index(tmp_path, entries)
        
        existing_filenames = {
            e.readable_filename for e in index.get_all()
            if e.readable_filename
        }
        
        assert "example-1.md" in existing_filenames
        assert "example-2.md" in existing_filenames

    def test_unique_filename_generation_with_existing(self, tmp_path):
        """Test unique filename generation respects existing files"""
        existing = {"example-test.md", "github-user-repo.md"}
        
        filename1 = FilenameGenerator.make_unique_filename("example-test.md", existing)
        filename2 = FilenameGenerator.make_unique_filename("new-file.md", existing)
        
        assert filename1 == "example-test-1.md"
        assert filename2 == "new-file.md"
