"""
Embedding storage and semantic search in SQLite.
Uses direct HTTP to an OpenAI-compatible embeddings endpoint.
"""
from __future__ import annotations

import json
import os
import sqlite3
import struct
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .search_documents import SearchDocument

EMBEDDING_TABLE = "embedding_store"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 256
EMBEDDING_BATCH_SIZE = 512
DOCUMENT_TEXT_BODY_LIMIT = 500
MIN_SIMILARITY_THRESHOLD = 0.3
DEFAULT_TIMEOUT = 30


@dataclass(frozen=True)
class EmbeddingMatch:
    path: str
    note_type: str
    url: str
    title: str
    summary: str
    similarity: float


# ---------------------------------------------------------------------------
# Embedding API
# ---------------------------------------------------------------------------


def get_embedding_config() -> dict[str, str] | None:
    api_key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not api_key:
        return None
    base_url = os.environ.get("EMBEDDING_BASE_URL") or os.environ.get(
        "OPENAI_BASE_URL", "https://openrouter.ai/api/v1"
    )
    model = os.environ.get("EMBEDDING_MODEL", EMBEDDING_MODEL)
    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url.rstrip("/"),
    }


def _call_embedding_api(
    texts: list[str],
    config: dict[str, str],
) -> list[list[float]]:
    payload = {
        "model": config.get("embedding_model", config.get("model", EMBEDDING_MODEL)),
        "input": texts,
        "dimensions": EMBEDDING_DIMENSIONS,
    }
    request = urllib.request.Request(
        f"{config['base_url']}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
        body = json.loads(response.read().decode("utf-8"))
    body["data"].sort(key=lambda item: item["index"])
    return [item["embedding"] for item in body["data"]]


def embed_texts(
    texts: list[str],
    config: dict[str, str],
) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        all_embeddings.extend(_call_embedding_api(batch, config))
    return all_embeddings


# ---------------------------------------------------------------------------
# Document text construction
# ---------------------------------------------------------------------------


def build_document_text(document: SearchDocument) -> str:
    parts = [
        document.title,
        document.url,
        document.tags,
        document.summary,
        document.body[:DOCUMENT_TEXT_BODY_LIMIT],
    ]
    return " | ".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# Vector serialization
# ---------------------------------------------------------------------------


def _normalize_vector(vector: list[float]) -> list[float]:
    magnitude = sum(x * x for x in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [x / magnitude for x in vector]


def _serialize_vector(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _deserialize_vector(data: bytes) -> list[float]:
    count = len(data) // 4
    return list(struct.unpack(f"<{count}f", data))


# ---------------------------------------------------------------------------
# SQLite storage
# ---------------------------------------------------------------------------


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _create_embedding_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {EMBEDDING_TABLE} (
            path TEXT PRIMARY KEY,
            note_type TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            embedding BLOB NOT NULL,
            mtime REAL NOT NULL
        )
        """
    )


def _load_stored_mtimes(connection: sqlite3.Connection) -> dict[str, float]:
    try:
        rows = connection.execute(
            f"SELECT path, mtime FROM {EMBEDDING_TABLE}"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {row["path"]: float(row["mtime"]) for row in rows}


def _delete_by_paths(connection: sqlite3.Connection, paths: set[str]) -> None:
    for path in paths:
        connection.execute(
            f"DELETE FROM {EMBEDDING_TABLE} WHERE path = ?", (path,)
        )


def _insert_embeddings(
    connection: sqlite3.Connection,
    documents: list[SearchDocument],
    embeddings: list[list[float]],
) -> None:
    connection.executemany(
        f"""
        INSERT OR REPLACE INTO {EMBEDDING_TABLE}
            (path, note_type, url, title, summary, embedding, mtime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(doc.path),
                doc.note_type,
                doc.url,
                doc.title,
                doc.summary,
                _serialize_vector(_normalize_vector(emb)),
                doc.path.stat().st_mtime,
            )
            for doc, emb in zip(documents, embeddings)
        ],
    )


# ---------------------------------------------------------------------------
# Index refresh (incremental)
# ---------------------------------------------------------------------------


def refresh_embeddings(
    documents: list[SearchDocument],
    *,
    database_path: Path,
    config: dict[str, str] | None = None,
) -> None:
    if config is None:
        config = get_embedding_config()
    if not config:
        raise ValueError(
            "No API key configured. Semantic search requires an embedding API."
        )

    connection = _connect(database_path)
    try:
        with connection:
            _create_embedding_table(connection)

        stored_mtimes = _load_stored_mtimes(connection)
        current_paths = {str(doc.path) for doc in documents}

        removed_paths = stored_mtimes.keys() - current_paths
        documents_to_embed: list[SearchDocument] = []
        for document in documents:
            path_str = str(document.path)
            if path_str not in stored_mtimes:
                documents_to_embed.append(document)
            elif document.path.stat().st_mtime != stored_mtimes[path_str]:
                documents_to_embed.append(document)

        if not removed_paths and not documents_to_embed:
            return

        with connection:
            if removed_paths:
                _delete_by_paths(connection, removed_paths)

            if documents_to_embed:
                texts = [build_document_text(doc) for doc in documents_to_embed]
                embeddings = embed_texts(texts, config)
                modified_paths = {
                    str(doc.path)
                    for doc in documents_to_embed
                    if str(doc.path) in stored_mtimes
                }
                if modified_paths:
                    _delete_by_paths(connection, modified_paths)
                _insert_embeddings(connection, documents_to_embed, embeddings)
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


def _cosine_similarities(
    query_vector: list[float],
    stored_vectors: list[list[float]],
) -> list[float]:
    try:
        import numpy as np

        q = np.array(query_vector, dtype=np.float32)
        m = np.array(stored_vectors, dtype=np.float32)
        return (m @ q).tolist()
    except ImportError:
        return [
            sum(a * b for a, b in zip(query_vector, stored))
            for stored in stored_vectors
        ]


def semantic_search(
    query: str,
    *,
    database_path: Path,
    config: dict[str, str] | None = None,
    note_type: str | None = None,
    limit: int = 10,
) -> list[EmbeddingMatch]:
    if config is None:
        config = get_embedding_config()
    if not config:
        raise ValueError(
            "No API key configured. Semantic search requires an embedding API."
        )

    query_embedding = _normalize_vector(embed_texts([query], config)[0])

    connection = _connect(database_path)
    try:
        where = ""
        params: list[str] = []
        if note_type:
            where = "WHERE note_type = ?"
            params = [note_type]

        rows = connection.execute(
            f"""
            SELECT path, note_type, url, title, summary, embedding
            FROM {EMBEDDING_TABLE}
            {where}
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return []

    stored_vectors = [_deserialize_vector(row["embedding"]) for row in rows]
    similarities = _cosine_similarities(query_embedding, stored_vectors)

    scored = sorted(
        zip(rows, similarities),
        key=lambda pair: pair[1],
        reverse=True,
    )

    return [
        EmbeddingMatch(
            path=str(row["path"]),
            note_type=str(row["note_type"]),
            url=str(row["url"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            similarity=round(similarity, 4),
        )
        for row, similarity in scored[:limit]
        if similarity >= MIN_SIMILARITY_THRESHOLD
    ]
