"""
SQLite FTS5 search index with BM25 ranking for memory notes.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .search_documents import SearchDocument

SEARCH_TABLE = "note_search"
MTIME_TABLE = "note_mtime"
BM25_WEIGHTS = (0.0, 0.0, 8.0, 4.0, 4.0, 3.0, 1.0)
QUERY_TERM_PATTERN = re.compile(r"[A-Za-z0-9+#-]{2,}")


@dataclass(frozen=True)
class SearchResult:
    path: str
    note_type: str
    url: str
    title: str
    summary: str
    score: float


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(f"DROP TABLE IF EXISTS {SEARCH_TABLE}")
    connection.execute(f"DROP TABLE IF EXISTS {MTIME_TABLE}")
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE {SEARCH_TABLE} USING fts5(
            path UNINDEXED,
            note_type UNINDEXED,
            title,
            url,
            tags,
            summary,
            body,
            tokenize='porter unicode61'
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE {MTIME_TABLE} (
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL
        )
        """
    )


def _schema_exists(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE name IN (?, ?)",
        (SEARCH_TABLE, MTIME_TABLE),
    ).fetchall()
    found = {row["name"] for row in rows}
    return SEARCH_TABLE in found and MTIME_TABLE in found


def _build_match_query(query: str) -> str:
    terms = QUERY_TERM_PATTERN.findall(query.lower())
    if not terms:
        raise ValueError("Search query must include at least one searchable term.")
    return " AND ".join(f"{term}*" for term in terms)


def _document_row(document: SearchDocument) -> tuple[str, ...]:
    return (
        str(document.path),
        document.note_type,
        document.title,
        document.url,
        document.tags,
        document.summary,
        document.body,
    )


def _insert_documents(
    connection: sqlite3.Connection,
    documents: list[SearchDocument],
) -> None:
    if not documents:
        return
    connection.executemany(
        f"""
        INSERT INTO {SEARCH_TABLE} (
            path, note_type, title, url, tags, summary, body
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [_document_row(doc) for doc in documents],
    )
    connection.executemany(
        f"INSERT OR REPLACE INTO {MTIME_TABLE} (path, mtime) VALUES (?, ?)",
        [(str(doc.path), doc.path.stat().st_mtime) for doc in documents],
    )


def _delete_by_paths(
    connection: sqlite3.Connection,
    paths: set[str],
) -> None:
    for path in paths:
        connection.execute(f"DELETE FROM {SEARCH_TABLE} WHERE path = ?", (path,))
        connection.execute(f"DELETE FROM {MTIME_TABLE} WHERE path = ?", (path,))


def _load_stored_mtimes(connection: sqlite3.Connection) -> dict[str, float]:
    rows = connection.execute(f"SELECT path, mtime FROM {MTIME_TABLE}").fetchall()
    return {row["path"]: float(row["mtime"]) for row in rows}


def rebuild_search_index(
    documents: list[SearchDocument],
    database_path: Path,
) -> None:
    connection = _connect(database_path)
    try:
        with connection:
            _create_schema(connection)
            _insert_documents(connection, documents)
    finally:
        connection.close()


def update_search_index(
    documents: list[SearchDocument],
    database_path: Path,
) -> None:
    connection = _connect(database_path)
    try:
        if not _schema_exists(connection):
            with connection:
                _create_schema(connection)
                _insert_documents(connection, documents)
            return

        stored_mtimes = _load_stored_mtimes(connection)
        current_paths = {str(doc.path) for doc in documents}

        removed_paths = stored_mtimes.keys() - current_paths
        new_documents: list[SearchDocument] = []
        modified_documents: list[SearchDocument] = []
        for document in documents:
            document_path = str(document.path)
            if document_path not in stored_mtimes:
                new_documents.append(document)
            elif document.path.stat().st_mtime != stored_mtimes[document_path]:
                modified_documents.append(document)

        if not removed_paths and not new_documents and not modified_documents:
            return

        modified_paths = {str(doc.path) for doc in modified_documents}
        with connection:
            _delete_by_paths(connection, removed_paths | modified_paths)
            _insert_documents(connection, new_documents + modified_documents)
    finally:
        connection.close()


def search_index(
    query: str,
    *,
    database_path: Path,
    note_type: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    match_expression = _build_match_query(query)

    where_clauses = [f"{SEARCH_TABLE} MATCH ?"]
    parameters: list[object] = [match_expression]

    if note_type:
        where_clauses.append("note_type = ?")
        parameters.append(note_type)

    parameters.append(limit)
    weight_list = ", ".join(str(w) for w in BM25_WEIGHTS)
    sql = f"""
        SELECT path, note_type, url, title, summary,
               -bm25({SEARCH_TABLE}, {weight_list}) AS score
        FROM {SEARCH_TABLE}
        WHERE {" AND ".join(where_clauses)}
        ORDER BY score DESC, title ASC
        LIMIT ?
    """

    connection = _connect(database_path)
    try:
        rows = connection.execute(sql, parameters).fetchall()
    finally:
        connection.close()

    return [
        SearchResult(
            path=str(row["path"]),
            note_type=str(row["note_type"]),
            url=str(row["url"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            score=float(row["score"]),
        )
        for row in rows
    ]
