"""
Data models for link organization and classification
"""
from dataclasses import dataclass
from typing import List, Optional, Any, Dict


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

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "link": self.link,
            "id": self.id,
            "filename": self.filename,
            "status": self.status
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