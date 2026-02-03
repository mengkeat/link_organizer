"""
Link extraction utilities for parsing URLs from markdown and text content.
"""

import re
from pathlib import Path


class LinkExtractor:
    """Extract HTTP/HTTPS links from text and files."""

    MD_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^\s)]+)\)")
    BARE_LINK_PATTERN = re.compile(r"(?<!\]\()(?<!\]\s)(https?://[^\s)]+)")

    @classmethod
    def extract_links_from_text(cls, content: str) -> list[str]:
        """
        Extract all HTTP/HTTPS links from text content.

        Args:
            content: Text content to extract links from

        Returns:
            Deduplicated list of URLs found in the content
        """
        md_links = cls.MD_LINK_PATTERN.findall(content)
        bare_links = cls.BARE_LINK_PATTERN.findall(content)
        links = list(dict.fromkeys(md_links + bare_links))
        return links

    @classmethod
    def extract_links_from_file(cls, filepath: str | Path) -> list[str]:
        """
        Extract all HTTP/HTTPS links from a file.

        Args:
            filepath: Path to the file to extract links from

        Returns:
            Deduplicated list of URLs found in the file
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.extract_links_from_text(content)


def extract_links_from_file(filepath: str | Path) -> list[str]:
    """
    Extract all HTTP/HTTPS links from a markdown file.

    This is a convenience function that wraps LinkExtractor.extract_links_from_file.

    Args:
        filepath: Path to the file to extract links from

    Returns:
        Deduplicated list of URLs found in the file
    """
    return LinkExtractor.extract_links_from_file(filepath)
