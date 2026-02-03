"""
Backwards compatibility wrapper for link extraction.

DEPRECATED: This module is deprecated. Use the CLI or import from src instead:
    from src.link_extractor import LinkExtractor, extract_links_from_file
"""

import warnings

from src.link_extractor import LinkExtractor, extract_links_from_file

__all__ = ["extract_links_from_file", "LinkExtractor"]


if __name__ == "__main__":
    warnings.warn(
        "get_count_links.py is deprecated. Use 'uv run python cli.py list' or "
        "import from src.link_extractor instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    links = extract_links_from_file("links.md")
    for link in links:
        print(link)
    print(f"Total: {len(links)}")
