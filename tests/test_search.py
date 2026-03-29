"""Tests for search_documents, search_index, and search orchestration."""
import sqlite3
from pathlib import Path

import pytest

from src.search_documents import (
    SearchDocument,
    _parse_frontmatter,
    _read_body_text,
    collect_search_documents,
)
from src.search_index import (
    SearchResult,
    rebuild_search_index,
    search_index,
    update_search_index,
)
from src.search import search_text, refresh_index


@pytest.fixture
def memory_dir(tmp_path):
    """Create a sample memory directory with link and topic notes."""
    links_dir = tmp_path / "links"
    links_dir.mkdir()
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()

    (links_dir / "note1.md").write_text(
        "---\nurl: https://example.com/article\ntitle: Example Article\n"
        "tags: [python, testing]\ntopic_id: abc123\n---\n\n"
        "# Example Article\n\nThis is about Python testing frameworks.\n",
        encoding="utf-8",
    )
    (links_dir / "note2.md").write_text(
        "---\nurl: https://example.com/rust\ntitle: Rust Guide\n"
        "tags: [rust, systems]\ntopic_id: def456\n---\n\n"
        "# Rust Guide\n\nA guide to Rust programming.\n",
        encoding="utf-8",
    )
    (topics_dir / "python.md").write_text(
        "---\ntopic_id: abc123\ntags: [python]\nsummary: Python topic hub\n---\n\n"
        "# Topic: Python\n\n### Example Article\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "search.db"


class TestSearchDocuments:
    def test_parse_frontmatter(self, memory_dir):
        note = memory_dir / "links" / "note1.md"
        meta = _parse_frontmatter(note)
        assert meta["url"] == "https://example.com/article"
        assert meta["title"] == "Example Article"
        assert meta["tags"] == ["python", "testing"]

    def test_parse_frontmatter_no_frontmatter(self, tmp_path):
        note = tmp_path / "plain.md"
        note.write_text("Just some text.\n")
        assert _parse_frontmatter(note) == {}

    def test_read_body_text(self, memory_dir):
        body = _read_body_text(memory_dir / "links" / "note1.md")
        assert "Python testing frameworks" in body
        assert "---" not in body

    def test_collect_search_documents(self, memory_dir):
        docs = collect_search_documents(notes_dir=memory_dir)
        assert len(docs) == 3
        types = {d.note_type for d in docs}
        assert "link" in types
        assert "topic" in types

    def test_note_type_inference(self, memory_dir):
        docs = collect_search_documents(notes_dir=memory_dir)
        link_docs = [d for d in docs if d.note_type == "link"]
        topic_docs = [d for d in docs if d.note_type == "topic"]
        assert len(link_docs) == 2
        assert len(topic_docs) == 1


class TestSearchIndex:
    def test_rebuild_and_search(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        results = search_index("python", database_path=db_path)
        assert len(results) >= 1
        titles = [r.title for r in results]
        assert any("Python" in t or "Example" in t for t in titles)

    def test_search_no_results(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        results = search_index("nonexistentterm", database_path=db_path)
        assert len(results) == 0

    def test_search_filter_by_type(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        results = search_index("python", database_path=db_path, note_type="topic")
        assert all(r.note_type == "topic" for r in results)

    def test_incremental_update(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        # Add a new note
        (memory_dir / "links" / "note3.md").write_text(
            "---\nurl: https://example.com/go\ntitle: Go Tutorial\n"
            "tags: [golang]\n---\n\n# Go Tutorial\n\nLearning Go.\n"
        )
        new_docs = collect_search_documents(notes_dir=memory_dir)
        update_search_index(new_docs, database_path=db_path)

        results = search_index("golang", database_path=db_path)
        assert len(results) >= 1

    def test_deleted_note_removed(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        # Delete a note
        (memory_dir / "links" / "note2.md").unlink()
        new_docs = collect_search_documents(notes_dir=memory_dir)
        update_search_index(new_docs, database_path=db_path)

        results = search_index("rust", database_path=db_path)
        assert len(results) == 0

    def test_invalid_query_raises(self, memory_dir, db_path):
        docs = collect_search_documents(notes_dir=memory_dir)
        rebuild_search_index(docs, database_path=db_path)

        with pytest.raises(ValueError, match="searchable term"):
            search_index("!@#$", database_path=db_path)


class TestSearchOrchestration:
    def test_search_text_end_to_end(self, memory_dir, db_path):
        results = search_text(
            "python",
            notes_dir=memory_dir,
            database_path=db_path,
        )
        assert len(results) >= 1
