"""
Tests for ContentProcessor
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.content_processor import ContentProcessor


class TestHashLink:
    """Test ContentProcessor.hash_link()"""

    def test_hash_consistent(self):
        """Test same input produces same hash"""
        url = "https://example.com"
        hash1 = ContentProcessor.hash_link(url)
        hash2 = ContentProcessor.hash_link(url)

        assert hash1 == hash2

    def test_hash_different_inputs(self):
        """Test different inputs produce different hashes"""
        hash1 = ContentProcessor.hash_link("https://example.com")
        hash2 = ContentProcessor.hash_link("https://different.com")

        assert hash1 != hash2

    def test_hash_length(self):
        """Test hash is SHA256 length (64 hex chars)"""
        hash_value = ContentProcessor.hash_link("https://example.com")

        assert len(hash_value) == 64

    def test_hash_hex_format(self):
        """Test hash is valid hexadecimal"""
        hash_value = ContentProcessor.hash_link("https://example.com")

        int(hash_value, 16)

    def test_hash_empty_string(self):
        """Test hashing empty string works"""
        hash_value = ContentProcessor.hash_link("")

        assert len(hash_value) == 64

    def test_hash_unicode(self):
        """Test hashing unicode content"""
        hash_value = ContentProcessor.hash_link("https://example.com/日本語")

        assert len(hash_value) == 64

    def test_hash_special_chars(self):
        """Test hashing URLs with special characters"""
        hash_value = ContentProcessor.hash_link(
            "https://example.com/path?query=value&foo=bar#section"
        )

        assert len(hash_value) == 64


class TestExtractContentFromFile:
    """Test ContentProcessor.extract_content_from_file()"""

    def test_extract_markdown(self, tmp_path):
        """Test extracting content from markdown file"""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\nSome content here.")

        content = ContentProcessor.extract_content_from_file(md_file)

        assert "# Title" in content
        assert "Some content here." in content

    def test_extract_markdown_utf8(self, tmp_path):
        """Test extracting UTF-8 content from markdown"""
        md_file = tmp_path / "test.md"
        md_file.write_text("# 日本語タイトル\n\n内容", encoding="utf-8")

        content = ContentProcessor.extract_content_from_file(md_file)

        assert "日本語タイトル" in content
        assert "内容" in content

    def test_unsupported_file_type(self, tmp_path):
        """Test handling unsupported file types"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Text content")

        content = ContentProcessor.extract_content_from_file(txt_file)

        assert "Unsupported file type: .txt" in content

    def test_unsupported_html_file(self, tmp_path):
        """Test HTML files are unsupported"""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Content</body></html>")

        content = ContentProcessor.extract_content_from_file(html_file)

        assert "Unsupported file type: .html" in content

    def test_nonexistent_file(self, tmp_path):
        """Test handling non-existent file"""
        content = ContentProcessor.extract_content_from_file(
            tmp_path / "nonexistent.md"
        )

        assert "Error reading file" in content

    def test_empty_markdown_file(self, tmp_path):
        """Test extracting from empty markdown file"""
        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        content = ContentProcessor.extract_content_from_file(md_file)

        assert content == ""

    def test_pdf_extraction(self, tmp_path):
        """Test PDF extraction is called for PDF files"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")

        with patch.object(
            ContentProcessor, "extract_pdf_text", return_value="Extracted PDF text"
        ) as mock_extract:
            content = ContentProcessor.extract_content_from_file(pdf_file)

            mock_extract.assert_called_once_with(pdf_file)
            assert content == "Extracted PDF text"

    def test_case_insensitive_extension(self, tmp_path):
        """Test file extensions are case-insensitive"""
        md_upper = tmp_path / "test.MD"
        md_upper.write_text("# Upper case extension")

        content = ContentProcessor.extract_content_from_file(md_upper)

        assert "# Upper case extension" in content


class TestExtractPdfText:
    """Test ContentProcessor.extract_pdf_text()"""

    def test_extract_pdf_text(self, tmp_path):
        """Test extracting text from PDF"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            content = ContentProcessor.extract_pdf_text(pdf_file)

        assert "Page 1 content" in content

    def test_extract_pdf_multiple_pages(self, tmp_path):
        """Test extracting text from multi-page PDF"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1"

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            content = ContentProcessor.extract_pdf_text(pdf_file)

        assert "Page 1" in content
        assert "Page 2" in content

    def test_extract_pdf_error(self, tmp_path):
        """Test handling PDF extraction errors"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"corrupt pdf")

        with patch("PyPDF2.PdfReader", side_effect=Exception("PDF error")):
            content = ContentProcessor.extract_pdf_text(pdf_file)

        assert "Error extracting PDF text" in content

    def test_extract_pdf_empty_pages(self, tmp_path):
        """Test PDF with empty pages"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            content = ContentProcessor.extract_pdf_text(pdf_file)

        assert content == "\n"


class TestGenerateTitleFromUrl:
    """Test ContentProcessor.generate_title_from_url()"""

    def test_simple_path(self):
        """Test generating title from simple path"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/my-article"
        )

        assert title == "My Article"

    def test_underscore_path(self):
        """Test path with underscores"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/my_great_article"
        )

        assert title == "My Great Article"

    def test_mixed_separators(self):
        """Test path with mixed separators"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/my-great_article"
        )

        assert title == "My Great Article"

    def test_trailing_slash(self):
        """Test URL with trailing slash"""
        title = ContentProcessor.generate_title_from_url("https://example.com/page/")

        assert title == ""

    def test_root_path(self):
        """Test root URL"""
        title = ContentProcessor.generate_title_from_url("https://example.com")

        assert title == "Example.Com"

    def test_deep_path(self):
        """Test deep nested path"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/docs/api/reference/endpoints"
        )

        assert title == "Endpoints"

    def test_file_extension(self):
        """Test URL with file extension"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/document.pdf"
        )

        assert title == "Document.Pdf"

    def test_numbers_in_path(self):
        """Test path with numbers"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/article-2023"
        )

        assert title == "Article 2023"

    def test_query_params_included(self):
        """Test URL with query params (they remain in last segment)"""
        title = ContentProcessor.generate_title_from_url(
            "https://example.com/search?q=test"
        )

        assert "Search" in title


class TestContentProcessorIntegration:
    """Integration tests for ContentProcessor"""

    def test_hash_and_extract_workflow(self, tmp_path):
        """Test typical workflow: hash URL, save content, extract"""
        url = "https://example.com/article"
        content_text = "# Article Title\n\nThis is the article content."

        link_hash = ContentProcessor.hash_link(url)

        md_file = tmp_path / f"{link_hash}.md"
        md_file.write_text(content_text)

        extracted = ContentProcessor.extract_content_from_file(md_file)

        assert extracted == content_text

    def test_title_matches_hash_uniqueness(self):
        """Test that similar URLs get unique hashes despite similar titles"""
        urls = [
            "https://example.com/my-article",
            "https://example.com/my-article-2",
            "https://different.com/my-article",
        ]

        hashes = [ContentProcessor.hash_link(url) for url in urls]

        assert len(set(hashes)) == 3
