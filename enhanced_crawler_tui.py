#!/usr/bin/env python3
"""
DEPRECATED: This module is deprecated. Use src.unified_crawler.UnifiedCrawler instead.

Enhanced Link Crawler with TUI Support - thin wrapper that calls UnifiedCrawler.
"""
import argparse
import asyncio
import warnings

from dotenv import load_dotenv

from src.link_extractor import extract_links_from_file
from src.unified_crawler import UnifiedCrawler

LINKS_MD = "links.md"


def main():
    """Main entry point with command line argument parsing for TUI crawler (deprecated)."""
    warnings.warn(
        "enhanced_crawler_tui.py is deprecated. Use 'python cli.py crawl --tui' or "
        "import UnifiedCrawler from src.unified_crawler instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("WARNING: enhanced_crawler_tui.py is deprecated. Use 'python cli.py crawl --tui' instead.")
    print()

    parser = argparse.ArgumentParser(description="Enhanced Link Crawler with TUI (DEPRECATED)")
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable TUI and run in console mode",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of worker threads (default: 5)",
    )

    args = parser.parse_args()

    load_dotenv()

    links = extract_links_from_file(LINKS_MD)
    print(f"Found {len(links)} links in {LINKS_MD}")

    crawler = UnifiedCrawler(
        incremental=False,
        use_tui=not args.no_tui,
        enable_classification=True,
        workers=args.workers,
    )
    asyncio.run(crawler.run(links))


if __name__ == "__main__":
    main()
