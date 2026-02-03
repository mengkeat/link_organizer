#!/usr/bin/env python3
"""
DEPRECATED: This module is deprecated. Use src.unified_crawler.UnifiedCrawler instead.

Enhanced Link Crawler with AI Classification - thin wrapper that calls UnifiedCrawler.
"""
import asyncio
import warnings

from dotenv import load_dotenv

from src.link_extractor import extract_links_from_file
from src.unified_crawler import UnifiedCrawler

LINKS_MD = "links.md"


def main():
    """Entry point for enhanced crawler with classification capabilities (deprecated)."""
    warnings.warn(
        "enhanced_crawler.py is deprecated. Use 'python cli.py crawl' or "
        "import UnifiedCrawler from src.unified_crawler instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("WARNING: enhanced_crawler.py is deprecated. Use 'python cli.py crawl' instead.")
    print()

    load_dotenv()

    links = extract_links_from_file(LINKS_MD)
    print(f"Found {len(links)} links in {LINKS_MD}")

    crawler = UnifiedCrawler(
        incremental=False,
        use_tui=False,
        enable_classification=True,
        workers=5,
    )
    asyncio.run(crawler.run(links))


if __name__ == "__main__":
    main()
