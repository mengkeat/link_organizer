"""
Router service: routes new links to existing or new topic files
based on embedding similarity.
"""

from pathlib import Path
from typing import Optional

import numpy as np

from .embedding_client import EmbeddingProvider
from .markdown_writer import MarkdownWriter
from .models import MemoryLinkEntry
from .topic_index_manager import TopicIndexManager


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class MemoryRouter:
    """Routes links to topic files based on embedding similarity."""

    def __init__(
        self,
        embedding_client: EmbeddingProvider,
        index_manager: TopicIndexManager,
        writer: MarkdownWriter,
        similarity_threshold: float = 0.75,
    ):
        self.embedding_client = embedding_client
        self.index_manager = index_manager
        self.writer = writer
        self.similarity_threshold = similarity_threshold

    async def route_link(
        self,
        entry: MemoryLinkEntry,
        content: str = "",
        title_for_new_topic: str = "",
    ) -> str:
        """Route a link to an existing or new topic. Returns topic_id."""
        # Build embedding input from URL + content
        embed_text = f"{entry.url}\n\n{content[:4000]}" if content else entry.url
        embedding = await self.embedding_client.embed(embed_text)

        # Find best matching topic
        best_topic_id, best_sim = self._find_best_topic(embedding)

        if best_topic_id and best_sim >= self.similarity_threshold:
            # Append to existing topic
            filename = self.index_manager.get_filename(best_topic_id)
            self.writer.append_link(filename, entry)
            self.index_manager.update_centroid(best_topic_id, embedding)
            self.index_manager.save()
            return best_topic_id
        else:
            # Create new topic
            topic_title = title_for_new_topic or entry.title or entry.url
            filename = self.writer.create_topic_file(
                topic_id="placeholder", title=topic_title, tags=entry.tags
            )
            topic_entry = self.index_manager.add_topic(
                filename=filename,
                initial_centroid=embedding,
                title=topic_title,
            )
            # Rewrite frontmatter with real topic_id
            self._fix_topic_id_in_file(filename, topic_entry.topic_id)
            # Append the first link entry
            self.writer.append_link(filename, entry)
            self.index_manager.save()
            return topic_entry.topic_id

    def _find_best_topic(
        self, embedding: np.ndarray
    ) -> tuple[Optional[str], float]:
        """Find the topic with highest cosine similarity to embedding."""
        centroids = self.index_manager.get_centroids()
        if not centroids:
            return None, 0.0

        best_id = None
        best_sim = -1.0
        for topic_id, centroid in centroids.items():
            sim = cosine_similarity(embedding, centroid)
            if sim > best_sim:
                best_sim = sim
                best_id = topic_id

        return best_id, best_sim

    def _fix_topic_id_in_file(self, filename: str, real_topic_id: str) -> None:
        """Replace placeholder topic_id in newly created file."""
        filepath = self.writer.topics_dir / filename
        content = filepath.read_text(encoding="utf-8")
        content = content.replace("topic_id: placeholder", f"topic_id: {real_topic_id}", 1)
        filepath.write_text(content, encoding="utf-8")
