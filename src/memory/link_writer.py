"""
Creates canonical per-link markdown notes containing metadata and source content.
"""

import hashlib
from datetime import datetime
from pathlib import Path

from .markdown_writer import slugify
from .models import MemoryLinkEntry


class LinkMarkdownWriter:
    """Writes one canonical markdown file per crawled link."""

    def __init__(self, links_dir: Path = Path("memory/links")):
        self.links_dir = links_dir
        self.links_dir.mkdir(parents=True, exist_ok=True)

    def write_link_note(
        self,
        entry: MemoryLinkEntry,
        topic_id: str = "",
        topic_filename: str = "",
    ) -> str:
        """Write canonical markdown note for a link and return relative path."""
        dt = datetime.now()
        year_dir = self.links_dir / dt.strftime("%Y")
        year_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(entry.title or entry.url, max_length=50)
        url_hash = hashlib.sha256(entry.url.encode("utf-8")).hexdigest()[:10]
        base = f"{dt.strftime('%Y-%m-%d')}-{slug or 'link'}-{url_hash}"
        filename = f"{base}.md"
        filepath = year_dir / filename

        counter = 2
        while filepath.exists():
            filename = f"{base}-{counter}.md"
            filepath = year_dir / filename
            counter += 1

        tags = entry.tags or []
        key_topics = entry.key_topics or []

        frontmatter = (
            "---\n"
            f"url: {entry.url}\n"
            f"title: {entry.title}\n"
            f"added_at: {entry.added_at}\n"
            f"content_type: {entry.content_type}\n"
            f"source_filename: {entry.source_filename}\n"
            f"topic_id: {topic_id}\n"
            f"topic_file: {topic_filename}\n"
            f"tags: {tags}\n"
            f"key_topics: {key_topics}\n"
            f"content_truncated: {entry.content_truncated}\n"
            "---\n\n"
        )

        content_block = entry.content_markdown or entry.raw_snippet or ""
        body = f"# {entry.title or entry.url}\n\n"
        if entry.summary:
            body += f"## Summary\n\n{entry.summary}\n\n"
        if entry.key_insight:
            body += f"## Key Insight\n\n{entry.key_insight}\n\n"
        body += "## Content\n\n"
        body += content_block.strip() + "\n"

        filepath.write_text(frontmatter + body, encoding="utf-8")

        relative_path = filepath.as_posix()
        return relative_path
