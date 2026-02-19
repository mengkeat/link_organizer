#!/usr/bin/env python3
"""
Link Organizer CLI - Command line interface for managing your link collection
"""
import argparse
import asyncio
import sys
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.logging_config import setup_logging, get_logger

logger = get_logger("cli")


def get_index():
    """Get LinkIndex instance."""
    from src.link_index import LinkIndex
    return LinkIndex(Path("index.json"))


def cmd_add(args):
    """Add one or more links to the collection."""
    from src.content_processor import ContentProcessor
    from src.link_index import LinkIndex, IndexEntry
    
    index = LinkIndex(Path("index.json"))
    added = 0
    
    for url in args.urls:
        if index.get(url):
            logger.warning("Duplicate link, already exists in index: %s", url)
            print(f"Already exists: {url}")
            continue
        
        entry = IndexEntry(
            link=url,
            id=ContentProcessor.hash_link(url),
            status="pending"
        )
        index.add(entry)
        added += 1
        print(f"Added: {url}")
    
    if added > 0:
        index.save()
        print(f"\nAdded {added} new link(s). Run 'link crawl' to fetch content.")


def cmd_list(args):
    """List links in the collection."""
    index = get_index()
    entries = index.get_all()
    
    if args.category:
        entries = [e for e in entries if e.classification and 
                   e.classification.get('category', '').lower() == args.category.lower()]
    
    if args.status:
        entries = [e for e in entries if args.status.lower() in e.status.lower()]
    
    if args.tag:
        entries = [e for e in entries if e.classification and
                   args.tag.lower() in [t.lower() for t in e.classification.get('tags', [])]]
    
    if not entries:
        print("No links found matching criteria.")
        return
    
    for i, entry in enumerate(entries[:args.limit], 1):
        status_icon = "[OK]" if entry.status == "Success" else "[X]" if entry.status.startswith("Failed") else "[.]"
        
        print(f"\n{i}. {status_icon} {entry.link}")
        
        if args.verbose and entry.classification:
            cat = entry.classification.get('category', 'N/A')
            tags = ', '.join(entry.classification.get('tags', [])[:3])
            summary = entry.classification.get('summary', '')[:100]
            print(f"   Category: {cat}")
            if tags:
                print(f"   Tags: {tags}")
            if summary:
                print(f"   Summary: {summary}...")
    
    total = len(entries)
    if total > args.limit:
        print(f"\n... and {total - args.limit} more. Use --limit to see more.")
    
    print(f"\nTotal: {total} links")


def cmd_search(args):
    """Search links by keyword."""
    index = get_index()
    results = index.search(args.query)
    
    if not results:
        print(f"No results found for '{args.query}'")
        return
    
    print(f"Found {len(results)} result(s) for '{args.query}':\n")
    
    for i, entry in enumerate(results[:args.limit], 1):
        status_icon = "[OK]" if entry.status == "Success" else "[X]"
        print(f"{i}. {status_icon} {entry.link}")
        
        if entry.classification:
            cat = entry.classification.get('category', '')
            summary = entry.classification.get('summary', '')[:80]
            if cat:
                print(f"   Category: {cat}")
            if summary:
                print(f"   {summary}...")
        print()


def cmd_stats(args):
    """Show statistics about the collection."""
    index = get_index()
    stats = index.get_stats()
    
    print("=== Link Collection Statistics ===\n")
    print(f"Total links:     {stats['total']}")
    print(f"Successfully saved: {stats['success']}")
    print(f"Failed:          {stats['failed']}")
    print(f"Pending:         {stats['pending']}")
    
    if stats.get('categories'):
        print("\n--- By Category ---")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")


def cmd_categories(args):
    """List all categories."""
    index = get_index()
    categories = index.list_categories()
    
    if not categories:
        print("No categories found. Run 'link crawl' to classify links.")
        return
    
    print("Categories:")
    for cat in categories:
        count = len(index.get_by_category(cat))
        print(f"  {cat} ({count})")


def cmd_tags(args):
    """List all tags."""
    index = get_index()
    tags = index.list_tags()
    
    if not tags:
        print("No tags found.")
        return
    
    print(f"Tags ({len(tags)} total):")
    print(", ".join(tags))


def _detect_duplicates(links: list[str]) -> list[str]:
    """Detect and log duplicate links. Returns deduplicated list."""
    seen = {}
    unique = []
    for link in links:
        if link in seen:
            seen[link] += 1
        else:
            seen[link] = 1
            unique.append(link)
    duplicates = {url: count for url, count in seen.items() if count > 1}
    if duplicates:
        for url, count in duplicates.items():
            logger.warning("Duplicate link found (%d occurrences): %s", count, url)
        logger.warning("Total duplicate links: %d", len(duplicates))
    return unique


def _run_crawl_and_route(links: list[str], index, *, incremental: bool = True,
                         use_tui: bool = False, workers: int = 5):
    """Shared crawl+classify+memory-route pipeline used by both crawl and memory-add."""
    from src.unified_crawler import UnifiedCrawler
    crawler = UnifiedCrawler(
        incremental=incremental,
        use_tui=use_tui,
        enable_classification=True,
        workers=workers,
    )
    asyncio.run(crawler.run(links, index))


def cmd_crawl(args):
    """Crawl and classify links."""
    load_dotenv()
    
    from src.link_extractor import extract_links_from_file
    from src.link_index import LinkIndex
    
    index = LinkIndex(Path("index.json"))
    
    # Determine which links to process
    if args.file:
        all_links = extract_links_from_file(args.file)
    else:
        all_links = extract_links_from_file("links.md")
    
    # Deduplicate extracted links
    all_links = _detect_duplicates(all_links)

    if args.retry:
        # Retry failed links
        links_to_process = list(index.get_failed_links())
        logger.info("Retrying %d failed links...", len(links_to_process))
    elif args.all:
        # Process all links
        links_to_process = all_links
        logger.info("Processing all %d links...", len(links_to_process))
    else:
        # Incremental: only new links
        existing = index.get_successful_links()
        links_to_process = [l for l in all_links if l not in existing]
        logger.info("Found %d total links, %d new to process.", len(all_links), len(links_to_process))
    
    if not links_to_process:
        logger.info("Nothing to process. Use --all to reprocess everything.")
        return
    
    _run_crawl_and_route(
        links_to_process, index,
        incremental=not args.all,
        use_tui=args.tui,
        workers=args.workers,
    )


def cmd_generate(args):
    """Generate static site from link collection."""
    from src.static_site_generator import StaticSiteGenerator, SiteConfig
    
    config = SiteConfig(
        title=args.title or "My Link Collection",
        description=args.description or "Organized collection of saved links",
        output_dir=args.output or "public"
    )
    
    generator = StaticSiteGenerator(config)
    
    index_file = Path("index.json")
    classifications_file = Path("classifications.json")
    
    if not index_file.exists():
        print("Error: index.json not found. Run 'link crawl' first.")
        sys.exit(1)
    
    output_dir = generator.generate(
        index_file, 
        classifications_file if classifications_file.exists() else None
    )
    
    print(f"\nStatic site generated successfully!")
    print(f"Open {output_dir / 'index.html'} in your browser to view.")


def cmd_export(args):
    """Export links to various formats."""
    index = get_index()
    entries = index.get_all()
    
    if args.format == "json":
        data = [e.to_dict() for e in entries]
        output = json.dumps(data, indent=2, ensure_ascii=False)
    elif args.format == "urls":
        output = "\n".join(e.link for e in entries)
    elif args.format == "markdown":
        lines = ["# Saved Links\n"]
        current_cat = None
        
        for entry in sorted(entries, key=lambda e: (
            e.classification.get('category', 'Uncategorized') if e.classification else 'Uncategorized',
            e.link
        )):
            cat = entry.classification.get('category', 'Uncategorized') if entry.classification else 'Uncategorized'
            if cat != current_cat:
                lines.append(f"\n## {cat}\n")
                current_cat = cat
            
            summary = ""
            if entry.classification and entry.classification.get('summary'):
                summary = f" - {entry.classification['summary'][:60]}..."
            
            lines.append(f"- [{entry.link[:60]}]({entry.link}){summary}")
        
        output = "\n".join(lines)
    else:
        print(f"Unknown format: {args.format}")
        return
    
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Exported to {args.output}")
    else:
        print(output)


def cmd_import(args):
    """Import links from a file."""
    from src.content_processor import ContentProcessor
    from src.link_index import LinkIndex, IndexEntry
    from src.link_extractor import extract_links_from_file
    
    index = LinkIndex(Path("index.json"))
    
    links = extract_links_from_file(args.file)
    added = 0
    
    for url in links:
        if index.get(url):
            continue
        
        entry = IndexEntry(
            link=url,
            id=ContentProcessor.hash_link(url),
            status="pending"
        )
        index.add(entry)
        added += 1
    
    if added > 0:
        index.save()
    
    print(f"Imported {added} new links from {args.file}")
    print(f"Run 'link crawl' to fetch and classify them.")


def cmd_memory_add(args):
    """Crawl specific URLs and route them into the memory system."""
    load_dotenv()

    from src.link_index import LinkIndex

    urls = _detect_duplicates(args.urls)
    index = LinkIndex(Path("index.json"))

    # Check which URLs are already successfully indexed
    existing = index.get_successful_links()
    new_urls = [u for u in urls if u not in existing]
    already_done = [u for u in urls if u in existing]
    for url in already_done:
        logger.info("Already indexed, re-routing to memory: %s", url)

    logger.info("memory-add: %d URL(s) to crawl, %d already indexed", len(new_urls), len(already_done))

    # Crawl new URLs through the full pipeline (fetch + classify + memory route)
    if new_urls:
        _run_crawl_and_route(new_urls, index, incremental=False, workers=1)

    # For already-indexed URLs, re-route them through memory in case they weren't routed before
    if already_done:
        _reroute_existing_to_memory(already_done, index)


def _reroute_existing_to_memory(urls: list[str], index):
    """Re-route already-indexed URLs into the memory system."""
    from src.config import get_config
    from src.content_processor import ContentProcessor
    from src.memory.embedding_client import LiteLLMEmbeddingClient
    from src.memory.link_writer import LinkMarkdownWriter
    from src.memory.markdown_writer import MarkdownWriter
    from src.memory.memory_router import MemoryRouter
    from src.memory.models import MemoryLinkEntry
    from src.memory.topic_index_manager import TopicIndexManager

    config = get_config()
    memory_dir = Path(config.memory.output_dir)
    topics_dir = memory_dir / config.memory.topics_subdir
    links_dir = memory_dir / config.memory.links_subdir

    embedding_client = LiteLLMEmbeddingClient(model=config.memory.embedding_model)
    index_manager = TopicIndexManager(memory_dir / "topic_index.db")
    writer = MarkdownWriter(topics_dir)
    router = MemoryRouter(
        embedding_client=embedding_client,
        index_manager=index_manager,
        writer=writer,
        similarity_threshold=config.memory.similarity_threshold,
    )
    link_writer = LinkMarkdownWriter(links_dir)

    for url in urls:
        entry = index.get(url)
        if not entry or not entry.classification:
            logger.warning("Skipping %s: no classification data available", url)
            continue

        classification = entry.classification
        title = ContentProcessor.generate_title_from_url(url)

        # Read content from saved file if available
        content_markdown = ""
        if entry.readable_filename:
            filepath = Path("dat") / entry.readable_filename
            if filepath.exists():
                content_markdown = ContentProcessor.extract_content_from_file(filepath)

        max_chars = config.memory.link_note_max_chars
        content_truncated = len(content_markdown) > max_chars

        topic_hints = [
            classification.get("category", ""),
            classification.get("subcategory", ""),
            *classification.get("tags", []),
            *classification.get("key_topics", []),
        ]
        topic_hints = [h for h in topic_hints if h]

        topic_title = (
            classification.get("subcategory")
            or classification.get("category")
            or title
        )

        memory_entry = MemoryLinkEntry(
            url=url,
            title=title,
            tags=classification.get("tags", []),
            summary=classification.get("summary", ""),
            key_insight=", ".join(classification.get("key_topics", [])),
            raw_snippet=content_markdown[:300],
            key_topics=classification.get("key_topics", []),
            content_markdown=content_markdown[:max_chars],
            source_filename=entry.readable_filename or "",
            content_type="md",
            content_truncated=content_truncated,
        )

        topic_id = asyncio.run(router.route_link(
            entry=memory_entry,
            content=content_markdown,
            title_for_new_topic=topic_title,
            topic_hints=topic_hints,
            append_to_topic=False,
        ))
        topic_filename = index_manager.get_filename(topic_id) or ""

        link_note_path = link_writer.write_link_note(
            entry=memory_entry,
            topic_id=topic_id,
            topic_filename=topic_filename,
        )
        memory_entry.link_note_path = link_note_path
        if topic_filename:
            writer.append_link(topic_filename, memory_entry)

        entry.memory_topic_id = topic_id
        entry.memory_topic_file = topic_filename
        entry.memory_link_file = link_note_path
        index.add(entry)
        logger.info("Re-routed %s -> topic %s", url, topic_filename)

    index.save()


def cmd_memory_topics(args):
    """List memory topics."""
    from src.config import get_config
    from src.memory.topic_index_manager import TopicIndexManager

    config = get_config()
    memory_dir = Path(config.memory.output_dir)
    index_manager = TopicIndexManager(memory_dir / "topic_index.db")

    topics = index_manager.list_topics()
    if not topics:
        print("No topics yet. Run migration or add links.")
        return

    for t in topics:
        print(f"  {t.filename:40s}  links: {t.link_count:3d}  {t.title[:50]}")
    print(f"\nTotal: {len(topics)} topics")


def cmd_remove(args):
    """Remove a link from the collection."""
    index = get_index()
    
    entry = index.get(args.url)
    if not entry:
        print(f"Link not found: {args.url}")
        return
    
    index.remove(args.url)
    index.save()
    print(f"Removed: {args.url}")


def main():
    parser = argparse.ArgumentParser(
        prog="link",
        description="Link Organizer - Manage your saved links collection"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # add command
    add_parser = subparsers.add_parser("add", help="Add links to collection")
    add_parser.add_argument("urls", nargs="+", help="URLs to add")
    add_parser.set_defaults(func=cmd_add)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List links")
    list_parser.add_argument("-c", "--category", help="Filter by category")
    list_parser.add_argument("-s", "--status", help="Filter by status (success/failed/pending)")
    list_parser.add_argument("-t", "--tag", help="Filter by tag")
    list_parser.add_argument("-l", "--limit", type=int, default=20, help="Max links to show")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show details")
    list_parser.set_defaults(func=cmd_list)
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search links")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-l", "--limit", type=int, default=10, help="Max results")
    search_parser.set_defaults(func=cmd_search)
    
    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.set_defaults(func=cmd_stats)
    
    # categories command
    cat_parser = subparsers.add_parser("categories", help="List categories")
    cat_parser.set_defaults(func=cmd_categories)
    
    # tags command
    tags_parser = subparsers.add_parser("tags", help="List tags")
    tags_parser.set_defaults(func=cmd_tags)
    
    # crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl and classify links")
    crawl_parser.add_argument("-f", "--file", help="Input markdown file (default: links.md)")
    crawl_parser.add_argument("--all", action="store_true", help="Reprocess all links")
    crawl_parser.add_argument("--retry", action="store_true", help="Retry failed links")
    crawl_parser.add_argument("--tui", action="store_true", help="Show TUI progress")
    crawl_parser.add_argument("-w", "--workers", type=int, default=5, help="Number of workers")
    crawl_parser.set_defaults(func=cmd_crawl)
    
    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate static site")
    gen_parser.add_argument("-o", "--output", help="Output directory (default: public)")
    gen_parser.add_argument("-t", "--title", help="Site title")
    gen_parser.add_argument("-d", "--description", help="Site description")
    gen_parser.set_defaults(func=cmd_generate)
    
    # export command
    export_parser = subparsers.add_parser("export", help="Export links")
    export_parser.add_argument("-f", "--format", choices=["json", "urls", "markdown"], 
                               default="json", help="Export format")
    export_parser.add_argument("-o", "--output", help="Output file")
    export_parser.set_defaults(func=cmd_export)
    
    # import command
    import_parser = subparsers.add_parser("import", help="Import links from file")
    import_parser.add_argument("file", help="Markdown file with links")
    import_parser.set_defaults(func=cmd_import)
    
    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a link")
    remove_parser.add_argument("url", help="URL to remove")
    remove_parser.set_defaults(func=cmd_remove)

    # memory-add command
    mem_add_parser = subparsers.add_parser("memory-add", help="Crawl URLs and route into memory")
    mem_add_parser.add_argument("urls", nargs="+", help="URLs to crawl and route into memory")
    mem_add_parser.set_defaults(func=cmd_memory_add)

    # memory-topics command
    mem_topics_parser = subparsers.add_parser("memory-topics", help="List memory topics")
    mem_topics_parser.set_defaults(func=cmd_memory_topics)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    setup_logging()
    args.func(args)


if __name__ == "__main__":
    main()
