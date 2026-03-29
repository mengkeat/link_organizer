"""
Collect and normalize markdown notes from memory/ into searchable documents.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .core import get_config

WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class SearchDocument:
    path: Path
    note_type: str
    title: str
    url: str
    topic_id: str
    tags: str
    summary: str
    body: str


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " ".join(parts)
    return WHITESPACE_PATTERN.sub(" ", str(value)).strip()


def _parse_frontmatter(note_path: Path) -> dict[str, object]:
    try:
        text = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {}
    if not text.startswith("---\n"):
        return {}
    frontmatter, _, _ = text[4:].partition("---\n")
    data: dict[str, object] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                data[key] = [
                    item.strip().strip("'").strip('"')
                    for item in inner.split(",")
                    if item.strip()
                ]
        else:
            data[key] = value.strip('"').strip("'")
    return data


def _read_body_text(note_path: Path) -> str:
    try:
        text = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
    if text.startswith("---\n"):
        _, _, text = text[4:].partition("---\n")
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _infer_note_type(note_path: Path, notes_dir: Path) -> str:
    try:
        rel = note_path.relative_to(notes_dir)
    except ValueError:
        return "other"
    parts = rel.parts
    if len(parts) >= 2:
        if parts[0] == "links":
            return "link"
        if parts[0] == "topics":
            return "topic"
    return "other"


def collect_search_documents(
    notes_dir: Path | None = None,
) -> list[SearchDocument]:
    if notes_dir is None:
        notes_dir = Path(get_config().memory.output_dir)
    documents: list[SearchDocument] = []
    if not notes_dir.exists():
        return documents
    for note_path in sorted(notes_dir.rglob("*.md")):
        metadata = _parse_frontmatter(note_path)
        note_type = _infer_note_type(note_path, notes_dir)
        documents.append(
            SearchDocument(
                path=note_path,
                note_type=note_type,
                title=_normalize_text(metadata.get("title")) or note_path.stem,
                url=_normalize_text(metadata.get("url")),
                topic_id=_normalize_text(metadata.get("topic_id")),
                tags=_normalize_text(metadata.get("tags")),
                summary=_normalize_text(metadata.get("summary")),
                body=_read_body_text(note_path),
            )
        )
    return documents
