"""
Data models for link organization and classification
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import time
from enum import Enum


@dataclass
class ClassificationResult:
    """Structured classification result"""
    category: str
    subcategory: str
    tags: List[str]
    summary: str
    confidence: float
    content_type: str
    difficulty: str
    quality_score: int
    key_topics: List[str]
    target_audience: str


@dataclass
class LinkData:
    """Represents a link and its associated data"""
    link: str
    id: str
    filename: Optional[str] = None
    status: str = "pending"
    content: Optional[str] = None
    classification: Optional[ClassificationResult] = None
    screenshot_filename: Optional[str] = None

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert LinkData to dictionary format for JSON serialization."""
        result = {
            "link": self.link,
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "screenshot_filename": self.screenshot_filename
        }
        
        if include_content and self.content:
            result["content"] = self.content
            
        if self.classification:
            result["classification"] = {
                "category": self.classification.category,
                "subcategory": self.classification.subcategory,
                "tags": self.classification.tags,
                "summary": self.classification.summary,
                "confidence": self.classification.confidence,
                "content_type": self.classification.content_type,
                "difficulty": self.classification.difficulty,
                "quality_score": self.classification.quality_score,
                "key_topics": self.classification.key_topics,
                "target_audience": self.classification.target_audience,
            }
        
        return result


class ProcessingStage(Enum):
    """Stages of link processing"""
    PENDING = "pending"
    FETCHING = "fetching"  
    FETCH_COMPLETE = "fetch_complete"
    CLASSIFYING = "classifying"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class WorkerStatus:
    """Status of an individual worker"""
    worker_id: str
    worker_type: str  # 'fetch' or 'classification'
    status: str = "idle"  # 'idle', 'working', 'error'
    current_task: Optional[str] = None
    last_update: float = field(default_factory=time.time)
    
    
@dataclass
class QueueStats:
    """Statistics for queue monitoring"""
    fetch_queue_size: int = 0
    classification_queue_size: int = 0
    completed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    start_time: float = field(default_factory=time.time)
    
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


@dataclass
class CrawlerConfig:
    """Configuration for crawler operations"""
    data_dir: str = "dat"
    index_file: str = "index.json"
    classifications_file: str = "classifications.json"
    max_retries: int = 3
    classification_workers: int = 5
    fetch_workers: int = 5
    request_delay: float = 1.0
    enable_tui: bool = False