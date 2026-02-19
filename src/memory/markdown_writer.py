"""
Writes and appends link entries to topic markdown files.
"""

import re
from datetime import datetime
from pathlib import Path

from .models import MemoryLinkEntry


def slugify(text: str, max_length: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")
    return text[:max_length]


class MarkdownWriter:
    """Handles creating and appending to topic markdown files."""

    def __init__(self, topics_dir: Path = Path("memory/topics")):
        self.topics_dir = topics_dir
        self.topics_dir.mkdir(parents=True, exist_ok=True)

    def create_topic_file(
        self, topic_id: str, title: str, tags: list[str] | None = None
    ) -> str:
        """Create a new topic markdown file with frontmatter. Returns filename."""
        slug = slugify(title) if title else topic_id
        filename = f"{slug}.md"
        filepath = self.topics_dir / filename

        # Handle collision
        counter = 2
        while filepath.exists():
            filename = f"{slug}_{counter}.md"
            filepath = self.topics_dir / filename
            counter += 1

        now = datetime.now().isoformat()
        frontmatter = (
            f"---\n"
            f"topic_id: {topic_id}\n"
            f"created_at: {now}\n"
            f"last_updated: {now}\n"
            f"tags: {tags or []}\n"
            f"summary: {title}\n"
            f"---\n\n"
            f"# Topic: {title or topic_id}\n"
        )
        filepath.write_text(frontmatter, encoding="utf-8")
        return filename

    def append_link(self, filename: str, entry: MemoryLinkEntry) -> None:
        """Append a link entry to an existing topic file."""
        filepath = self.topics_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Topic file not found: {filepath}")

        # Update last_updated in frontmatter
        self._update_last_updated(filepath)

        date_str = datetime.now().strftime("%Y-%m-%d")
        title_display = entry.title or entry.url

        tags_str = " ".join(f"#{t}" for t in entry.tags) if entry.tags else ""

        block = f"\n## [[{date_str}]] {title_display}\n"
        block += f"- **URL:** {entry.url}\n"
        if entry.link_note_path:
            block += f"- **Link Note:** [{title_display}]({entry.link_note_path})\n"
        if tags_str:
            block += f"- **Tags:** {tags_str}\n"
        if entry.summary:
            block += f"- **Summary:** {entry.summary}\n"
        if entry.key_insight:
            block += f"- **Key Insight:** {entry.key_insight}\n"
        if entry.raw_snippet:
            block += f'- **Raw Snippet:** > "{entry.raw_snippet}"\n'

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(block)

    def _update_last_updated(self, filepath: Path) -> None:
        """Update the last_updated field in frontmatter."""
        content = filepath.read_text(encoding="utf-8")
        now = datetime.now().isoformat()
        updated = re.sub(
            r"^(last_updated:).*$",
            f"\\1 {now}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if updated != content:
            filepath.write_text(updated, encoding="utf-8")
