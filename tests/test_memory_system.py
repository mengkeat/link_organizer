"""
Tests for the topic-based memory system.

Verifies:
1. Adding 10 links produces correct topic files
2. Adding 11th link does NOT modify content of files from first 10 (except target)
3. Topic index centroids update correctly
4. New topic creation when no match
"""

import hashlib
import pytest
import numpy as np
from pathlib import Path

from src.memory.topic_index_manager import TopicIndexManager
from src.memory.markdown_writer import MarkdownWriter, slugify
from src.memory.memory_router import MemoryRouter, cosine_similarity
from src.memory.models import MemoryLinkEntry, TopicEntry, TopicIndex


# --- Deterministic fake embedding client ---

class FakeEmbeddingClient:
    """Returns deterministic embeddings based on URL hash for testing."""

    def __init__(self, cluster_map: dict[str, np.ndarray] | None = None):
        """
        cluster_map: optional dict mapping URL substrings to fixed vectors.
        If URL contains a key, that vector is returned.
        Otherwise, a hash-based vector is generated.
        """
        self.cluster_map = cluster_map or {}

    async def embed(self, text: str) -> np.ndarray:
        for key, vec in self.cluster_map.items():
            if key in text:
                return vec
        # Deterministic hash-based embedding
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = np.array([int(h[i:i+2], 16) / 255.0 for i in range(0, 20, 2)], dtype=np.float64)
        return vec / (np.linalg.norm(vec) + 1e-10)


# --- Unit tests ---

class TestCosineSimlarity:
    def test_identical_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector(self):
        a = np.array([1.0, 2.0])
        b = np.zeros(2)
        assert cosine_similarity(a, b) == 0.0


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello_world"

    def test_special_chars(self):
        assert slugify("AI/ML & Data!") == "ai_ml_data"

    def test_max_length(self):
        long = "a" * 100
        assert len(slugify(long, max_length=60)) == 60


class TestTopicIndexManager:
    def test_add_topic(self, tmp_path):
        mgr = TopicIndexManager(tmp_path / "topic_index.db")
        vec = np.array([1.0, 0.0, 0.0])
        entry = mgr.add_topic("test.md", vec, title="Test Topic")

        assert entry.link_count == 1
        assert mgr.topic_count == 1
        assert mgr.get_filename(entry.topic_id) == "test.md"

    def test_update_centroid(self, tmp_path):
        mgr = TopicIndexManager(tmp_path / "topic_index.db")
        vec1 = np.array([1.0, 0.0, 0.0])
        entry = mgr.add_topic("test.md", vec1)

        vec2 = np.array([0.0, 1.0, 0.0])
        mgr.update_centroid(entry.topic_id, vec2)

        topic = mgr.get_topic(entry.topic_id)
        assert topic.link_count == 2
        expected = (vec1 * 1 + vec2) / 2
        np.testing.assert_array_almost_equal(
            np.array(topic.centroid_vector), expected
        )

    def test_save_and_reload(self, tmp_path):
        path = tmp_path / "topic_index.db"
        mgr = TopicIndexManager(path)
        mgr.embedding_model = "test-model"
        vec = np.array([0.5, 0.5])
        mgr.add_topic("file.md", vec, title="Saved Topic")
        mgr.save()

        mgr2 = TopicIndexManager(path)
        assert mgr2.topic_count == 1
        assert mgr2.embedding_model == "test-model"
        topics = mgr2.list_topics()
        assert topics[0].title == "Saved Topic"

    def test_get_centroids(self, tmp_path):
        mgr = TopicIndexManager(tmp_path / "topic_index.db")
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        e1 = mgr.add_topic("a.md", v1)
        e2 = mgr.add_topic("b.md", v2)

        centroids = mgr.get_centroids()
        assert len(centroids) == 2
        np.testing.assert_array_equal(centroids[e1.topic_id], v1)
        np.testing.assert_array_equal(centroids[e2.topic_id], v2)


class TestMarkdownWriter:
    def test_create_topic_file(self, tmp_path):
        writer = MarkdownWriter(topics_dir=tmp_path)
        filename = writer.create_topic_file("abc123", "Machine Learning")

        assert filename == "machine_learning.md"
        content = (tmp_path / filename).read_text(encoding="utf-8")
        assert "topic_id: abc123" in content
        assert "# Topic: Machine Learning" in content

    def test_append_link(self, tmp_path):
        writer = MarkdownWriter(topics_dir=tmp_path)
        filename = writer.create_topic_file("abc123", "Test Topic")

        entry = MemoryLinkEntry(
            url="https://example.com",
            title="Example Page",
            tags=["web", "test"],
            summary="A test page",
        )
        writer.append_link(filename, entry)

        content = (tmp_path / filename).read_text(encoding="utf-8")
        assert "https://example.com" in content
        assert "#web #test" in content
        assert "A test page" in content

    def test_collision_handling(self, tmp_path):
        writer = MarkdownWriter(topics_dir=tmp_path)
        f1 = writer.create_topic_file("id1", "Same Name")
        f2 = writer.create_topic_file("id2", "Same Name")

        assert f1 != f2
        assert (tmp_path / f1).exists()
        assert (tmp_path / f2).exists()


class TestMemoryRouterImmutability:
    """Core test: verify that adding the 11th link does NOT modify
    content of files created by the first 10 links (except the target)."""

    @pytest.mark.asyncio
    async def test_immutability(self, tmp_path):
        topics_dir = tmp_path / "topics"
        index_path = tmp_path / "topic_index.db"

        # Create two clusters: links with "cluster_a" go to one topic,
        # links with "cluster_b" go to another.
        vec_a = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        vec_b = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

        fake_embedder = FakeEmbeddingClient(
            cluster_map={"cluster_a": vec_a, "cluster_b": vec_b}
        )
        index_mgr = TopicIndexManager(index_path)
        writer = MarkdownWriter(topics_dir)
        router = MemoryRouter(
            embedding_client=fake_embedder,
            index_manager=index_mgr,
            writer=writer,
            similarity_threshold=0.75,
        )

        # Add 10 links: 5 to cluster_a, 5 to cluster_b
        for i in range(5):
            entry = MemoryLinkEntry(
                url=f"https://cluster_a.com/page{i}",
                title=f"Cluster A Page {i}",
                tags=["a"],
                summary=f"Content about cluster A topic {i}",
            )
            await router.route_link(entry, content=f"cluster_a content {i}")

        for i in range(5):
            entry = MemoryLinkEntry(
                url=f"https://cluster_b.com/page{i}",
                title=f"Cluster B Page {i}",
                tags=["b"],
                summary=f"Content about cluster B topic {i}",
            )
            await router.route_link(entry, content=f"cluster_b content {i}")

        # Record state of all topic files after 10 links
        file_hashes_before = {}
        for f in topics_dir.iterdir():
            file_hashes_before[f.name] = f.read_text(encoding="utf-8")

        # Record topic index state
        index_before = {
            t.topic_id: (t.link_count, list(t.centroid_vector))
            for t in index_mgr.list_topics()
        }

        assert len(file_hashes_before) == 2, "Should have exactly 2 topic files"

        # Add 11th link to cluster_a
        entry_11 = MemoryLinkEntry(
            url="https://cluster_a.com/page_new",
            title="Cluster A New Page",
            tags=["a"],
            summary="New content for cluster A",
        )
        topic_id_11 = await router.route_link(entry_11, content="cluster_a new content")

        # Verify: the target file was appended to
        target_filename = index_mgr.get_filename(topic_id_11)
        assert target_filename is not None

        # Verify: all OTHER files are unchanged
        for f in topics_dir.iterdir():
            if f.name == target_filename:
                # Target file should have new content appended
                new_content = f.read_text(encoding="utf-8")
                old_content = file_hashes_before[f.name]
                # Old content should be a prefix (except for last_updated in frontmatter)
                # Check the link entries are preserved
                assert "cluster_a.com/page0" in new_content
                assert "cluster_a.com/page_new" in new_content
            else:
                # Non-target files must be byte-identical
                assert f.read_text(encoding="utf-8") == file_hashes_before[f.name], \
                    f"File {f.name} was modified but shouldn't have been!"

        # Verify topic index: only the target topic changed
        for topic in index_mgr.list_topics():
            if topic.topic_id == topic_id_11:
                old_count = index_before[topic.topic_id][0]
                assert topic.link_count == old_count + 1
            else:
                assert topic.link_count == index_before[topic.topic_id][0]
                assert topic.centroid_vector == index_before[topic.topic_id][1]

    @pytest.mark.asyncio
    async def test_new_topic_creation(self, tmp_path):
        """Verify that a dissimilar link creates a new topic file."""
        topics_dir = tmp_path / "topics"
        index_path = tmp_path / "topic_index.db"

        vec_a = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
        vec_c = np.array([0.0, 0.0, 0.0, 0.0, 1.0])

        fake_embedder = FakeEmbeddingClient(
            cluster_map={"cluster_a": vec_a, "outlier": vec_c}
        )
        index_mgr = TopicIndexManager(index_path)
        writer = MarkdownWriter(topics_dir)
        router = MemoryRouter(
            embedding_client=fake_embedder,
            index_manager=index_mgr,
            writer=writer,
            similarity_threshold=0.75,
        )

        # Add one link to cluster_a
        entry1 = MemoryLinkEntry(
            url="https://cluster_a.com/page1",
            title="Cluster A",
        )
        await router.route_link(entry1, content="cluster_a stuff")

        assert index_mgr.topic_count == 1

        # Add a dissimilar link
        entry2 = MemoryLinkEntry(
            url="https://outlier.com/unique",
            title="Outlier Content",
        )
        await router.route_link(entry2, content="outlier topic")

        assert index_mgr.topic_count == 2

    @pytest.mark.asyncio
    async def test_centroid_update_correctness(self, tmp_path):
        """Verify centroid running average is computed correctly."""
        topics_dir = tmp_path / "topics"
        index_path = tmp_path / "topic_index.db"

        vec = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.2, 0.0])  # Close to vec, should match

        call_count = 0

        class SequentialEmbedder:
            async def embed(self, text):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return vec
                return vec2

        index_mgr = TopicIndexManager(index_path)
        writer = MarkdownWriter(topics_dir)
        router = MemoryRouter(
            embedding_client=SequentialEmbedder(),
            index_manager=index_mgr,
            writer=writer,
            similarity_threshold=0.5,
        )

        entry1 = MemoryLinkEntry(url="https://example.com/a", title="First")
        await router.route_link(entry1)

        entry2 = MemoryLinkEntry(url="https://example.com/b", title="Second")
        topic_id = await router.route_link(entry2)

        # Should have 1 topic with 2 links
        assert index_mgr.topic_count == 1
        topic = index_mgr.get_topic(topic_id)
        assert topic.link_count == 2

        expected_centroid = (vec + vec2) / 2
        np.testing.assert_array_almost_equal(
            np.array(topic.centroid_vector), expected_centroid
        )
