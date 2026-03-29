#!/usr/bin/env python3
"""CLI interface for the link organizer."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .core import setup_logging, get_logger, get_config
from .index import LinkIndex, LinkExtractor, IndexEntry

logger = get_logger("cli")


def get_index():
    return LinkIndex(Path(get_config().crawler.index_file))


def _detect_duplicates(links: list[str]) -> list[str]:
    unique = list(dict.fromkeys(links))
    if len(unique) < len(links):
        logger.warning("Removed %d duplicate links", len(links) - len(unique))
    return unique


async def cmd_sync(args):
    """Sync links from a file (default links.md) to the collection."""
    load_dotenv()
    config = get_config()
    input_file = args.file or config.default_input_file

    if not Path(input_file).exists():
        print(f"Error: {input_file} not found. Please create it or specify a file with -f.")
        return

    links = LinkExtractor.extract_links_from_file(input_file)
    links = _detect_duplicates(links)

    if not links:
        print(f"No links found in {input_file}.")
        return

    from .crawler import UnifiedCrawler

    crawler = UnifiedCrawler(workers=args.workers, incremental=not args.all)
    await crawler.run(links)

    # Best-effort search index refresh after sync
    try:
        from .search import refresh_index
        refresh_index()
        logger.info("Search index updated.")
    except Exception:
        logger.warning("Search index refresh failed", exc_info=True)


def cmd_list(args):
    index = get_index()
    entries = index.get_all()
    if args.category:
        entries = [
            e for e in entries
            if e.classification and e.classification.get('category', '').lower() == args.category.lower()
        ]
    if args.status:
        entries = [e for e in entries if args.status.lower() in e.status.lower()]

    for i, entry in enumerate(entries[:args.limit], 1):
        status = "[OK]" if entry.status == "Success" else "[X]" if "Failed" in entry.status else "[.]"
        print(f"{i}. {status} {entry.link}")
    print(f"\nTotal: {len(entries)} links")


def cmd_search(args):
    """Search memory notes using FTS5, semantic, or hybrid search."""
    load_dotenv()
    from .search import search

    mode = args.mode or get_config().search.default_mode
    results = search(
        args.query,
        mode=mode,
        note_type=args.type,
        limit=args.limit,
        rebuild=args.rebuild,
    )
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        if r.url:
            print(f"   URL: {r.url}")
        print(f"   Type: {r.note_type}  Score: {r.score:.6g}")
        if r.summary:
            desc = r.summary[:160].rstrip() + ("..." if len(r.summary) > 160 else "")
            print(f"   {desc}")
        print(f"   Path: {r.path}")
        print()
    print(f"Found {len(results)} results")


def cmd_stats(args):
    index = get_index()
    entries = index.get_all()
    success = len([e for e in entries if e.status == "Success"])
    failed = len([e for e in entries if "Failed" in e.status])
    print(f"Total: {len(entries)}")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Pending: {len(entries) - success - failed}")


def cmd_export(args):
    index = get_index()
    entries = index.get_all()
    if args.format == "json":
        data = [e.to_dict() for e in entries]
        output = json.dumps(data, indent=2, ensure_ascii=False)
    elif args.format == "urls":
        output = "\n".join(e.link for e in entries)
    else:
        print(f"Unknown format: {args.format}")
        return

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Exported to {args.output}")
    else:
        print(output)


def cmd_reindex(args):
    """Rebuild the search index from memory/ notes."""
    load_dotenv()
    from .search import refresh_index

    refresh_index(rebuild=args.rebuild)
    print("Search index updated.")


def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        prog="link",
        description="Link Organizer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync links from file to collection")
    sync_parser.add_argument("-f", "--file", help="Input file (default links.md)")
    sync_parser.add_argument("--all", action="store_true", help="Reprocess all links")
    sync_parser.add_argument("--workers", type=int, default=5, help="Number of workers")

    # list
    list_parser = subparsers.add_parser("list", help="List links")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=50, help="Max links to show")

    # search
    search_parser = subparsers.add_parser("search", help="Search memory notes")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--mode", choices=["text", "semantic", "hybrid"],
        help="Search mode (default: text)",
    )
    search_parser.add_argument(
        "--type", choices=["link", "topic"],
        help="Filter by note type",
    )
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument(
        "--rebuild", action="store_true",
        help="Force full index rebuild",
    )

    # stats
    subparsers.add_parser("stats", help="Show statistics")

    # export
    export_parser = subparsers.add_parser("export", help="Export links")
    export_parser.add_argument("-f", "--format", choices=["json", "urls"], default="json")
    export_parser.add_argument("-o", "--output", help="Output file")

    # reindex
    reindex_parser = subparsers.add_parser("reindex", help="Rebuild the search index")
    reindex_parser.add_argument(
        "--rebuild", action="store_true", default=True,
        help="Full rebuild (default)",
    )

    args = parser.parse_args()
    if args.command == "sync":
        asyncio.run(cmd_sync(args))
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "reindex":
        cmd_reindex(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
