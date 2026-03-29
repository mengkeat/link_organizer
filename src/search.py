"""
Unified search orchestration: FTS5 text search, semantic search, and hybrid.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .core import get_config, get_logger
from .search_documents import SearchDocument, collect_search_documents
from .search_index import (
    SearchResult,
    rebuild_search_index,
    search_index,
    update_search_index,
)

logger = get_logger("search")

DEFAULT_SEARCH_LIMIT = 10


def refresh_index(
    *,
    notes_dir: Path | None = None,
    database_path: Path | None = None,
    rebuild: bool = False,
) -> None:
    config = get_config()
    if notes_dir is None:
        notes_dir = Path(config.memory.output_dir)
    if database_path is None:
        database_path = Path(config.search.db_file)
    documents = collect_search_documents(notes_dir=notes_dir)
    if rebuild:
        rebuild_search_index(documents, database_path=database_path)
    else:
        update_search_index(documents, database_path=database_path)


def search_text(
    query: str,
    *,
    notes_dir: Path | None = None,
    database_path: Path | None = None,
    note_type: str | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
    rebuild: bool = False,
) -> list[SearchResult]:
    config = get_config()
    if database_path is None:
        database_path = Path(config.search.db_file)
    refresh_index(
        notes_dir=notes_dir,
        database_path=database_path,
        rebuild=rebuild,
    )
    return search_index(
        query,
        database_path=database_path,
        note_type=note_type,
        limit=limit,
    )


def search_semantic(
    query: str,
    *,
    notes_dir: Path | None = None,
    database_path: Path | None = None,
    note_type: str | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
) -> list[SearchResult]:
    from .embeddings import EmbeddingMatch, refresh_embeddings, semantic_search

    config = get_config()
    if notes_dir is None:
        notes_dir = Path(config.memory.output_dir)
    if database_path is None:
        database_path = Path(config.search.db_file)
    documents = collect_search_documents(notes_dir=notes_dir)
    refresh_embeddings(documents, database_path=database_path)
    matches = semantic_search(
        query,
        database_path=database_path,
        note_type=note_type,
        limit=limit,
    )
    return [
        SearchResult(
            path=m.path,
            note_type=m.note_type,
            url=m.url,
            title=m.title,
            summary=m.summary,
            score=m.similarity,
        )
        for m in matches
    ]


def search_hybrid(
    query: str,
    *,
    notes_dir: Path | None = None,
    database_path: Path | None = None,
    note_type: str | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
    rebuild: bool = False,
) -> list[SearchResult]:
    text_results = search_text(
        query,
        notes_dir=notes_dir,
        database_path=database_path,
        note_type=note_type,
        limit=limit * 2,
        rebuild=rebuild,
    )
    try:
        sem_results = search_semantic(
            query,
            notes_dir=notes_dir,
            database_path=database_path,
            note_type=note_type,
            limit=limit * 2,
        )
    except (ValueError, Exception) as exc:
        logger.warning("Semantic search unavailable, using text only: %s", exc)
        sem_results = []

    # Reciprocal Rank Fusion
    k = 60
    scores: dict[str, float] = {}
    result_map: dict[str, SearchResult] = {}

    for rank, r in enumerate(text_results):
        scores[r.path] = scores.get(r.path, 0.0) + 1.0 / (k + rank + 1)
        result_map[r.path] = r

    for rank, r in enumerate(sem_results):
        scores[r.path] = scores.get(r.path, 0.0) + 1.0 / (k + rank + 1)
        if r.path not in result_map:
            result_map[r.path] = r

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        SearchResult(
            path=result_map[path].path,
            note_type=result_map[path].note_type,
            url=result_map[path].url,
            title=result_map[path].title,
            summary=result_map[path].summary,
            score=round(score, 6),
        )
        for path, score in ranked[:limit]
    ]


def search(
    query: str,
    *,
    mode: str = "text",
    note_type: str | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
    rebuild: bool = False,
) -> list[SearchResult]:
    if mode == "semantic":
        return search_semantic(query, note_type=note_type, limit=limit)
    elif mode == "hybrid":
        return search_hybrid(
            query, note_type=note_type, limit=limit, rebuild=rebuild
        )
    else:
        return search_text(
            query, note_type=note_type, limit=limit, rebuild=rebuild
        )
