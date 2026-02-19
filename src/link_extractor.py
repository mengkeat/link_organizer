"""
Link extraction utilities for parsing URLs from markdown and text content.
"""

import re
from pathlib import Path

from src.logging_config import get_logger

logger = get_logger("link_extractor")


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
        all_links = md_links + bare_links
        duplicates = [u for u in dict.fromkeys(all_links) if all_links.count(u) > 1]
        if duplicates:
            logger.warning("Duplicate links found: %s", duplicates)
        links = list(dict.fromkeys(all_links))
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
        logger.info("Extracting links from %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        links = cls.extract_links_from_text(content)
        logger.info("Found %d links in %s", len(links), filepath)
        return links


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
