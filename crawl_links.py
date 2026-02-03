#!/usr/bin/env python3
"""
DEPRECATED: This module is deprecated. Use src.unified_crawler.UnifiedCrawler instead.

Basic link crawler - thin wrapper that calls UnifiedCrawler.
"""
import asyncio
import warnings

from get_count_links import extract_links_from_file
from src.unified_crawler import UnifiedCrawler

LINKS_MD = "links.md"


def main():
    """Entry point for the basic crawler script (deprecated)."""
    warnings.warn(
        "crawl_links.py is deprecated. Use 'python cli.py crawl' or "
        "import UnifiedCrawler from src.unified_crawler instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("WARNING: crawl_links.py is deprecated. Use 'python cli.py crawl' instead.")
    print()

    links = extract_links_from_file(LINKS_MD)
    print(f"Found {len(links)} links in {LINKS_MD}")

    crawler = UnifiedCrawler(
        incremental=False,
        use_tui=False,
        enable_classification=False,
        workers=12,
    )
    asyncio.run(crawler.run(links))


if __name__ == "__main__":
    main()
