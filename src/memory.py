"""
Topic-based memory system for link organization.
"""
import os
import re
import uuid
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Protocol
import numpy as np
from pydantic import BaseModel, Field
from .core import get_logger

logger = get_logger("memory")

# --- Models ---

class TopicEntry(BaseModel):
    topic_id: str
    filename: str
    centroid_vector: List[float]
    link_count: int = Field(ge=0, default=0)
    title: str = ""

class MemoryLinkEntry(BaseModel):
    url: str
    title: str = ""
    tags: List[str] = Field(default_factory=list)
    summary: str = ""
    key_insight: str = ""
    raw_snippet: str = ""
    key_topics: List[str] = Field(default_factory=list)
    content_markdown: str = ""
    source_filename: str = ""
    content_type: str = ""
    link_note_path: str = ""
    content_truncated: bool = False
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# --- Utilities ---

def slugify(text: str, max_length: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")
    return text[:max_length]

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0: return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

# --- Components ---

class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> np.ndarray: ...

class LiteLLMEmbeddingClient:
    def __init__(self, model: str = "openrouter/openai/text-embedding-3-small", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")

    async def embed(self, text: str) -> np.ndarray:
        import litellm
        response = await litellm.aembedding(model=self.model, input=[text[:8000]], api_key=self.api_key)
        return np.array(response.data[0]["embedding"], dtype=np.float64)

class TopicIndexManager:
    def __init__(self, db_path: Path = Path(".cache/topic_index.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS topics (topic_id TEXT PRIMARY KEY, filename TEXT NOT NULL, centroid_vector BLOB NOT NULL, link_count INTEGER DEFAULT 0, title TEXT DEFAULT '');
        """)
        self._conn.commit()

    def save(self): self._conn.commit()

    @property
    def embedding_model(self) -> str:
        row = self._conn.execute("SELECT value FROM metadata WHERE key = 'embedding_model'").fetchone()
        return row[0] if row else ""

    @embedding_model.setter
    def embedding_model(self, value: str):
        self._conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('embedding_model', ?)", (value,))

    def get_centroids(self) -> Dict[str, np.ndarray]:
        rows = self._conn.execute("SELECT topic_id, centroid_vector FROM topics").fetchall()
        return {row[0]: np.frombuffer(row[1], dtype=np.float64) for row in rows}

    def get_topic(self, topic_id: str) -> Optional[TopicEntry]:
        row = self._conn.execute("SELECT topic_id, filename, centroid_vector, link_count, title FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        if not row: return None
        return TopicEntry(topic_id=row[0], filename=row[1], centroid_vector=np.frombuffer(row[2], dtype=np.float64).tolist(), link_count=row[3], title=row[4])

    def get_filename(self, topic_id: str) -> Optional[str]:
        row = self._conn.execute("SELECT filename FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        return row[0] if row else None

    def add_topic(self, filename: str, initial_centroid: np.ndarray, title: str = "", topic_id: str = "") -> TopicEntry:
        if not topic_id:
            topic_id = uuid.uuid4().hex[:12]
        self._conn.execute("INSERT INTO topics (topic_id, filename, centroid_vector, link_count, title) VALUES (?, ?, ?, ?, ?)",
                           (topic_id, filename, initial_centroid.astype(np.float64).tobytes(), 1, title))
        return TopicEntry(topic_id=topic_id, filename=filename, centroid_vector=initial_centroid.tolist(), link_count=1, title=title)

    def update_centroid(self, topic_id: str, new_vector: np.ndarray):
        row = self._conn.execute("SELECT centroid_vector, link_count FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        if not row: return
        old_centroid, n = np.frombuffer(row[0], dtype=np.float64), row[1]
        new_centroid = (old_centroid * n + new_vector) / (n + 1)
        self._conn.execute("UPDATE topics SET centroid_vector = ?, link_count = ? WHERE topic_id = ?", (new_centroid.tobytes(), n + 1, topic_id))

    def list_topics(self) -> List[TopicEntry]:
        rows = self._conn.execute("SELECT topic_id, filename, centroid_vector, link_count, title FROM topics").fetchall()
        return [TopicEntry(topic_id=row[0], filename=row[1], centroid_vector=np.frombuffer(row[2], dtype=np.float64).tolist(), link_count=row[3], title=row[4]) for row in rows]

    @property
    def topic_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]

class MarkdownWriter:
    def __init__(self, topics_dir: Path = Path("memory/topics")):
        self.topics_dir = topics_dir
        self.topics_dir.mkdir(parents=True, exist_ok=True)

    def create_topic_file(self, topic_id: str, title: str, tags: Optional[List[str]] = None) -> str:
        slug = slugify(title) or topic_id
        filename = f"{slug}.md"
        filepath = self.topics_dir / filename
        counter = 2
        while filepath.exists():
            filename = f"{slug}_{counter}.md"; filepath = self.topics_dir / filename; counter += 1
        
        frontmatter = f"---\ntopic_id: {topic_id}\ncreated_at: {datetime.now().isoformat()}\ntags: {tags or []}\nsummary: {title}\n---\n\n# Topic: {title}\n"
        filepath.write_text(frontmatter, encoding="utf-8")
        return filename

    def append_link(self, filename: str, entry: MemoryLinkEntry):
        filepath = self.topics_dir / filename
        tags_str = " ".join([f"#{t}" for t in entry.tags])
        content = f"\n### [{entry.title or entry.url}]({entry.url})\n- Added: {entry.added_at}\n- Tags: {tags_str}\n- Summary: {entry.summary}\n"
        if entry.link_note_path: content += f"- Link Note: {entry.link_note_path}\n"
        with open(filepath, "a", encoding="utf-8") as f: f.write(content)

class LinkMarkdownWriter:
    def __init__(self, links_dir: Path = Path("memory/links")):
        self.links_dir = links_dir
        self.links_dir.mkdir(parents=True, exist_ok=True)

    def write_link_note(self, entry: MemoryLinkEntry, topic_id: str = "", topic_filename: str = "") -> str:
        slug = slugify(entry.title or entry.url, max_length=50)
        url_hash = hashlib.sha256(entry.url.encode("utf-8")).hexdigest()[:10]
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-{slug or 'link'}-{url_hash}.md"
        filepath = self.links_dir / filename
        
        frontmatter = f"---\nurl: {entry.url}\ntitle: {entry.title}\ntags: {entry.tags}\ntopic_id: {topic_id}\n---\n\n# {entry.title or entry.url}\n\n## Summary\n{entry.summary}\n\n## Content\n{entry.content_markdown or entry.raw_snippet}\n"
        filepath.write_text(frontmatter, encoding="utf-8")
        return str(filepath)

# --- Router ---

class MemoryRouter:
    def __init__(self, embedding_client: EmbeddingProvider, index_manager: TopicIndexManager, writer: MarkdownWriter, similarity_threshold: float = 0.75):
        self.embedding_client = embedding_client
        self.index_manager = index_manager
        self.writer = writer
        self.similarity_threshold = similarity_threshold

    async def route_link(self, entry: MemoryLinkEntry, content: str = "", title_for_new_topic: str = "", topic_hints: Optional[List[str]] = None) -> str:
        embed_text = f"{entry.url}\n\n{content[:4000]}"
        if topic_hints: embed_text += f"\n\nHints: {' | '.join(topic_hints)}"
        embedding = await self.embedding_client.embed(embed_text)
        
        centroids = self.index_manager.get_centroids()
        best_topic_id, best_sim = None, -1.0
        for tid, centroid in centroids.items():
            sim = cosine_similarity(embedding, centroid)
            if sim > best_sim: best_topic_id, best_sim = tid, sim
            
        if best_topic_id and best_sim >= self.similarity_threshold:
            filename = self.index_manager.get_topic(best_topic_id).filename
            self.writer.append_link(filename, entry)
            self.index_manager.update_centroid(best_topic_id, embedding)
            self.index_manager.save()
            return best_topic_id
        else:
            topic_title = title_for_new_topic or entry.title or entry.url
            topic_id = uuid.uuid4().hex[:12]
            filename = self.writer.create_topic_file(topic_id, topic_title, entry.tags)
            topic_entry = self.index_manager.add_topic(filename, embedding, topic_title, topic_id=topic_id)
            self.writer.append_link(filename, entry)
            self.index_manager.save()
            return topic_entry.topic_id
