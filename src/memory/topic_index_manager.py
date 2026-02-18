"""
Manages the topic index SQLite database for topic centroids.
"""

import sqlite3
import uuid
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .models import TopicEntry


class TopicIndexManager:
    """Manages topic index DB: centroid storage, lookup, and updates."""

    def __init__(self, db_path: Path = Path("memory/topic_index.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS topics (
                topic_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                centroid_vector BLOB NOT NULL,
                link_count INTEGER DEFAULT 0,
                title TEXT DEFAULT ''
            );
        """)
        self._conn.commit()

    def save(self) -> None:
        """Commit the current SQLite transaction."""
        self._conn.commit()

    @property
    def embedding_model(self) -> str:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'embedding_model'"
        ).fetchone()
        return row[0] if row else ""

    @embedding_model.setter
    def embedding_model(self, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('embedding_model', ?)",
            (value,),
        )

    def _row_to_entry(self, row: tuple) -> TopicEntry:
        """Convert a DB row to a TopicEntry."""
        topic_id, filename, centroid_blob, link_count, title = row
        centroid_vector = np.frombuffer(centroid_blob, dtype=np.float64).tolist()
        return TopicEntry(
            topic_id=topic_id,
            filename=filename,
            centroid_vector=centroid_vector,
            link_count=link_count,
            title=title,
        )

    def get_centroids(self) -> Dict[str, np.ndarray]:
        """Return mapping of topic_id -> centroid vector."""
        rows = self._conn.execute(
            "SELECT topic_id, centroid_vector FROM topics"
        ).fetchall()
        return {
            row[0]: np.frombuffer(row[1], dtype=np.float64) for row in rows
        }

    def get_topic(self, topic_id: str) -> Optional[TopicEntry]:
        """Get a specific topic entry by ID."""
        row = self._conn.execute(
            "SELECT topic_id, filename, centroid_vector, link_count, title "
            "FROM topics WHERE topic_id = ?",
            (topic_id,),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def get_filename(self, topic_id: str) -> Optional[str]:
        """Get filename for a topic."""
        row = self._conn.execute(
            "SELECT filename FROM topics WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        return row[0] if row else None

    def list_topics(self) -> list[TopicEntry]:
        """List all topic entries."""
        rows = self._conn.execute(
            "SELECT topic_id, filename, centroid_vector, link_count, title FROM topics"
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def add_topic(
        self, filename: str, initial_centroid: np.ndarray, title: str = ""
    ) -> TopicEntry:
        """Create a new topic entry in the index."""
        topic_id = uuid.uuid4().hex[:12]
        centroid_blob = initial_centroid.astype(np.float64).tobytes()
        self._conn.execute(
            "INSERT INTO topics (topic_id, filename, centroid_vector, link_count, title) "
            "VALUES (?, ?, ?, ?, ?)",
            (topic_id, filename, centroid_blob, 1, title),
        )
        return TopicEntry(
            topic_id=topic_id,
            filename=filename,
            centroid_vector=initial_centroid.tolist(),
            link_count=1,
            title=title,
        )

    def update_centroid(self, topic_id: str, new_vector: np.ndarray) -> None:
        """Update a topic's centroid using running average."""
        row = self._conn.execute(
            "SELECT centroid_vector, link_count FROM topics WHERE topic_id = ?",
            (topic_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Topic not found: {topic_id}")

        old_centroid = np.frombuffer(row[0], dtype=np.float64)
        n = row[1]
        new_centroid = (old_centroid * n + new_vector) / (n + 1)

        self._conn.execute(
            "UPDATE topics SET centroid_vector = ?, link_count = ? WHERE topic_id = ?",
            (new_centroid.tobytes(), n + 1, topic_id),
        )

    @property
    def topic_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM topics").fetchone()
        return row[0]
