"""
Pydantic models for the topic-based memory system
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TopicEntry(BaseModel):
    """A single topic in the sidecar index."""

    topic_id: str
    filename: str
    centroid_vector: List[float]
    link_count: int = Field(ge=0, default=0)
    title: str = ""


class TopicIndex(BaseModel):
    """Root model for topic index."""

    embedding_model: str = ""
    topics: List[TopicEntry] = Field(default_factory=list)


class MemoryLinkEntry(BaseModel):
    """Data for a single link to be written into a topic markdown file."""

    url: str
    title: str = ""
    tags: List[str] = Field(default_factory=list)
    summary: str = ""
    key_insight: str = ""
    raw_snippet: str = ""
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat())
