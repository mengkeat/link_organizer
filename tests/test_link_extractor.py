"""
Tests for LinkExtractor
"""

import pytest
from pathlib import Path
from src.link_extractor import LinkExtractor, extract_links_from_file


class TestLinkExtractorFromText:
    """Test LinkExtractor.extract_links_from_text()"""

    def test_extract_markdown_links(self):
        """Test extracting markdown format links [text](url)"""
        content = """
        Check out [Python docs](https://docs.python.org) for more info.
        Also see [GitHub](https://github.com/user/repo) for the code.
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 2
        assert "https://docs.python.org" in links
        assert "https://github.com/user/repo" in links

    def test_extract_bare_urls(self):
        """Test extracting bare URLs without markdown formatting"""
        content = """
        Visit https://example.com for more info.
        Also check http://test.org/page
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 2
        assert "https://example.com" in links
        assert "http://test.org/page" in links

    def test_extract_mixed_links(self):
        """Test extracting both markdown and bare URLs"""
        content = """
        [Docs](https://docs.python.org)
        Visit https://example.com directly
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 2
        assert "https://docs.python.org" in links
        assert "https://example.com" in links

    def test_deduplication(self):
        """Test that duplicate links are removed"""
        content = """
        [Link1](https://example.com)
        [Link2](https://example.com)
        https://example.com
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert links[0] == "https://example.com"

    def test_empty_content(self):
        """Test extracting from empty content"""
        links = LinkExtractor.extract_links_from_text("")
        assert links == []

    def test_no_links(self):
        """Test content with no links"""
        content = "This is plain text without any links."
        links = LinkExtractor.extract_links_from_text(content)
        assert links == []

    def test_link_with_query_params(self):
        """Test links with query parameters"""
        content = "[Search](https://example.com/search?q=python&lang=en)"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://example.com/search?q=python&lang=en" in links

    def test_link_with_fragment(self):
        """Test links with URL fragments"""
        content = "[Docs](https://example.com/docs#section1)"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://example.com/docs#section1" in links

    def test_link_with_port(self):
        """Test links with port numbers"""
        content = "http://localhost:8080/api/test"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "http://localhost:8080/api/test" in links

    def test_preserves_order(self):
        """Test that links preserve order of first appearance"""
        content = """
        [First](https://first.com)
        [Second](https://second.com)
        [Third](https://third.com)
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert links == [
            "https://first.com",
            "https://second.com",
            "https://third.com",
        ]

    def test_markdown_link_before_bare(self):
        """Test markdown links are extracted before bare URLs"""
        content = """
        [Markdown](https://markdown.com)
        https://bare.com
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert links[0] == "https://markdown.com"
        assert links[1] == "https://bare.com"

    def test_url_in_parentheses(self):
        """Test bare URL inside parentheses (not markdown)"""
        content = "See the docs (https://docs.example.com) for more info."
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://docs.example.com" in links

    def test_multiple_links_same_line(self):
        """Test multiple links on the same line"""
        content = "[A](https://a.com) and [B](https://b.com) and https://c.com"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 3
        assert "https://a.com" in links
        assert "https://b.com" in links
        assert "https://c.com" in links

    def test_link_with_special_chars_in_path(self):
        """Test links with special characters in path"""
        content = "[Paper](https://arxiv.org/abs/2105.00613)"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://arxiv.org/abs/2105.00613" in links

    def test_nested_brackets_in_link_text(self):
        """Test markdown links with brackets in link text - regex doesn't support nested"""
        content = "[[text]](https://example.com)"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 0

    def test_simple_bracket_link_text(self):
        """Test standard markdown links are extracted"""
        content = "[text](https://example.com)"
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://example.com" in links

    def test_only_http_https(self):
        """Test that only http/https links are extracted"""
        content = """
        ftp://ftp.example.com
        mailto:user@example.com
        https://valid.com
        """
        links = LinkExtractor.extract_links_from_text(content)

        assert len(links) == 1
        assert "https://valid.com" in links


class TestLinkExtractorFromFile:
    """Test LinkExtractor.extract_links_from_file()"""

    def test_extract_from_markdown_file(self, tmp_path):
        """Test extracting links from a markdown file"""
        md_file = tmp_path / "links.md"
        md_file.write_text(
            """
# My Links

- [Python](https://python.org)
- [GitHub](https://github.com)

Bare link: https://example.com
"""
        )

        links = LinkExtractor.extract_links_from_file(md_file)

        assert len(links) == 3
        assert "https://python.org" in links
        assert "https://github.com" in links
        assert "https://example.com" in links

    def test_extract_from_file_with_path_string(self, tmp_path):
        """Test extracting using string path instead of Path object"""
        md_file = tmp_path / "links.md"
        md_file.write_text("[Link](https://example.com)")

        links = LinkExtractor.extract_links_from_file(str(md_file))

        assert len(links) == 1
        assert "https://example.com" in links

    def test_empty_file(self, tmp_path):
        """Test extracting from empty file"""
        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        links = LinkExtractor.extract_links_from_file(md_file)

        assert links == []

    def test_file_with_only_whitespace(self, tmp_path):
        """Test extracting from file with only whitespace"""
        md_file = tmp_path / "whitespace.md"
        md_file.write_text("   \n\n   \t   \n")

        links = LinkExtractor.extract_links_from_file(md_file)

        assert links == []

    def test_file_not_found(self, tmp_path):
        """Test handling of non-existent file"""
        with pytest.raises(FileNotFoundError):
            LinkExtractor.extract_links_from_file(tmp_path / "nonexistent.md")

    def test_large_file(self, tmp_path):
        """Test extracting from file with many links"""
        md_file = tmp_path / "many_links.md"
        links_content = "\n".join(
            [f"[Link{i}](https://example{i}.com)" for i in range(100)]
        )
        md_file.write_text(links_content)

        links = LinkExtractor.extract_links_from_file(md_file)

        assert len(links) == 100

    def test_utf8_content(self, tmp_path):
        """Test extracting from file with UTF-8 content"""
        md_file = tmp_path / "utf8.md"
        md_file.write_text(
            "[日本語リンク](https://example.com/日本語)",
            encoding="utf-8",
        )

        links = LinkExtractor.extract_links_from_file(md_file)

        assert len(links) == 1


class TestConvenienceFunction:
    """Test the module-level extract_links_from_file function"""

    def test_convenience_function(self, tmp_path):
        """Test that convenience function wraps the class method"""
        md_file = tmp_path / "links.md"
        md_file.write_text("[Link](https://example.com)")

        links = extract_links_from_file(md_file)

        assert len(links) == 1
        assert "https://example.com" in links

    def test_convenience_function_matches_class_method(self, tmp_path):
        """Test convenience function returns same result as class method"""
        md_file = tmp_path / "links.md"
        md_file.write_text(
            """
[Link1](https://a.com)
https://b.com
[Link2](https://c.com)
"""
        )

        class_result = LinkExtractor.extract_links_from_file(md_file)
        func_result = extract_links_from_file(md_file)

        assert class_result == func_result
