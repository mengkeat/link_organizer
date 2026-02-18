#!/usr/bin/env python3
"""
Migration script: converts existing index.json data into topic-based markdown files.

Uses greedy threshold clustering (same logic as the router) to form initial topics.
After this one-time run, use the router for all future additions.

Usage:
    uv run python scripts/migrate_to_memory.py
    uv run python scripts/migrate_to_memory.py --threshold 0.80
    uv run python scripts/migrate_to_memory.py --dry-run
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.content_processor import ContentProcessor
from src.link_index import LinkIndex
from src.memory.embedding_client import LiteLLMEmbeddingClient
from src.memory.markdown_writer import MarkdownWriter
from src.memory.memory_router import MemoryRouter
from src.memory.models import MemoryLinkEntry
from src.memory.topic_index_manager import TopicIndexManager


async def migrate(
    threshold: float = 0.75,
    memory_dir: str = "memory",
    dry_run: bool = False,
    embedding_model: str = "openai/text-embedding-3-small",
):
    """Migrate existing links to topic-based markdown memory."""
    load_dotenv()

    index = LinkIndex(Path("index.json"))
    entries = index.get_all()
    successful = [e for e in entries if e.status == "Success"]

    print(f"Found {len(entries)} total links, {len(successful)} successfully crawled.")

    if not successful:
        print("No successfully crawled links to migrate.")
        return

    # Initialize components
    memory_path = Path(memory_dir)
    topics_dir = memory_path / "topics"
    index_path = memory_path / "topic_index.db"

    embedding_client = LiteLLMEmbeddingClient(model=embedding_model)
    index_manager = TopicIndexManager(db_path=index_path)
    index_manager.embedding_model = embedding_model
    writer = MarkdownWriter(topics_dir=topics_dir)
    router = MemoryRouter(
        embedding_client=embedding_client,
        index_manager=index_manager,
        writer=writer,
        similarity_threshold=threshold,
    )

    print(f"Similarity threshold: {threshold}")
    print(f"Output directory: {memory_path}")
    if dry_run:
        print("DRY RUN - no files will be written")
    print()

    processed = 0
    errors = 0

    for entry in successful:
        # Load content from dat/ directory
        content = ""
        if entry.filename:
            file_path = Path("dat") / entry.filename
            if file_path.exists():
                content = ContentProcessor.extract_content_from_file(file_path)

        # Build a memory link entry
        title = ""
        summary = ""
        tags = []
        key_insight = ""

        if entry.classification:
            title = entry.classification.get("summary", "")[:100]
            summary = entry.classification.get("summary", "")
            tags = entry.classification.get("tags", [])
            key_insight = ", ".join(entry.classification.get("key_topics", []))

        if not title:
            title = ContentProcessor.generate_title_from_url(entry.link)

        link_entry = MemoryLinkEntry(
            url=entry.link,
            title=title,
            tags=tags,
            summary=summary,
            key_insight=key_insight,
            raw_snippet=content[:200] if content else "",
        )

        if dry_run:
            print(f"  [DRY] Would route: {entry.link[:80]}")
            processed += 1
            continue

        try:
            topic_id = await router.route_link(
                entry=link_entry,
                content=content,
                title_for_new_topic=title,
            )
            processed += 1
            topic = index_manager.get_topic(topic_id)
            print(f"  [{processed}/{len(successful)}] -> {topic.filename} ({topic.title[:40]})")
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {entry.link[:60]}: {e}")

    print(f"\nMigration complete: {processed} processed, {errors} errors")
    print(f"Topics created: {index_manager.topic_count}")


def main():
    parser = argparse.ArgumentParser(description="Migrate links to topic-based memory")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Similarity threshold (default: 0.75)",
    )
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="Output directory (default: memory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )
    parser.add_argument(
        "--embedding-model",
        default="openai/text-embedding-3-small",
        help="Embedding model to use",
    )
    args = parser.parse_args()

    asyncio.run(
        migrate(
            threshold=args.threshold,
            memory_dir=args.memory_dir,
            dry_run=args.dry_run,
            embedding_model=args.embedding_model,
        )
    )


if __name__ == "__main__":
    main()
