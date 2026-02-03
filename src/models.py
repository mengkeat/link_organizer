"""
Data models for link organization and classification
"""

import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ClassificationResult(BaseModel):
    """Structured classification result"""

    category: str
    subcategory: str
    tags: List[str]
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    content_type: str
    difficulty: str
    quality_score: int = Field(ge=1, le=10)
    key_topics: List[str]
    target_audience: str

    @field_validator("tags")
    @classmethod
    def tags_non_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("tags must be a non-empty list")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization (backwards compatibility)."""
        return self.model_dump()


class LinkData(BaseModel):
    """Represents a link and its associated data"""

    link: str
    id: str
    filename: Optional[str] = None
    status: str = "pending"
    content: Optional[str] = None
    classification: Optional[ClassificationResult] = None
    screenshot_filename: Optional[str] = None

    model_config = {"validate_assignment": True}

    @field_validator("link")
    @classmethod
    def validate_url(cls, v: str) -> str:
        url_pattern = re.compile(
            r"^https?://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        if not url_pattern.match(v):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "fetching", "fetch_complete", "classifying", "success", "failed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert LinkData to dictionary format for JSON serialization."""
        result = {
            "link": self.link,
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "screenshot_filename": self.screenshot_filename,
        }

        if include_content and self.content:
            result["content"] = self.content

        if self.classification:
            result["classification"] = self.classification.model_dump()

        return result


class ProcessingStage(Enum):
    """Stages of link processing"""

    PENDING = "pending"
    FETCHING = "fetching"
    FETCH_COMPLETE = "fetch_complete"
    CLASSIFYING = "classifying"
    SUCCESS = "success"
    FAILED = "failed"


class WorkerStatus(BaseModel):
    """Status of an individual worker"""

    worker_id: str
    worker_type: str  # 'fetch' or 'classification'
    status: str = "idle"  # 'idle', 'working', 'error'
    current_task: Optional[str] = None
    last_update: float = Field(default_factory=time.time)


class QueueStats(BaseModel):
    """Statistics for queue monitoring"""

    fetch_queue_size: int = 0
    classification_queue_size: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    start_time: float = Field(default_factory=time.time)

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on completed and total counts."""
        if self.total_count == 0:
            return 0.0
        return ((self.completed_count + self.failed_count) / self.total_count) * 100

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since start in seconds."""
        return time.time() - self.start_time


class CrawlerConfig(BaseModel):
    """Configuration for crawler operations"""

    data_dir: str = "dat"
    index_file: str = "index.json"
    classifications_file: str = "classifications.json"
    max_retries: int = Field(default=3, gt=0)
    classification_workers: int = Field(default=5, gt=0)
    fetch_workers: int = Field(default=5, gt=0)
    request_delay: float = Field(default=1.0, ge=0.0)
    enable_tui: bool = False
