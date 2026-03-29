"""
Core configuration, models, and logging for the link organizer.
"""
import logging
import sys
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import yaml
from pydantic import BaseModel, Field, field_validator

# --- Logging ---

LOG_FILE = Path("link_organizer.log")

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root application logger."""
    logger = logging.getLogger("link_organizer")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    return logger

def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the application root."""
    return logging.getLogger(f"link_organizer.{name}")

# --- Config ---

@dataclass
class ClassificationConfig:
    """Classification-related configuration"""
    categories: List[str] = field(default_factory=lambda: [
        "Technology", "Science", "AI/ML", "Programming",
        "Research", "Tutorial", "News", "Blog", "Documentation",
        "Business", "Design", "Security", "Data Science", "Web Development"
    ])
    content_types: List[str] = field(default_factory=lambda: [
        "tutorial", "guide", "documentation", "research_paper",
        "blog_post", "news_article", "reference", "course", "tool"
    ])

@dataclass
class CrawlerConfigSettings:
    """Crawler-related configuration"""
    data_dir: str = ".cache/dat"
    index_file: str = ".cache/index.json"
    classifications_file: str = ".cache/classifications.json"
    max_retries: int = 3
    classification_workers: int = 5
    fetch_workers: int = 5
    request_delay: float = 1.0
    enable_tui: bool = False

@dataclass
class MemoryConfig:
    """Memory system configuration"""
    output_dir: str = "memory"
    topics_subdir: str = "topics"
    links_subdir: str = "links"
    topic_index_db: str = ".cache/topic_index.db"
    link_note_max_chars: int = 120000
    similarity_threshold: float = 0.75
    embedding_model: str = "openrouter/openai/text-embedding-3-small"

@dataclass
class SearchConfig:
    """Search index configuration"""
    db_file: str = ".cache/search.db"
    default_mode: str = "text"

@dataclass
class Config:
    """Main configuration class for link organizer"""
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    crawler: CrawlerConfigSettings = field(default_factory=CrawlerConfigSettings)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    default_input_file: str = "links.md"
    
    _instance: Optional["Config"] = field(default=None, init=False, repr=False)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        if config_path is None:
            config_path = Path("config.yaml")
        if not config_path.exists():
            return cls()
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        config = cls()
        if "classification" in data:
            class_data = data["classification"]
            if "categories" in class_data: config.classification.categories = class_data["categories"]
            if "content_types" in class_data: config.classification.content_types = class_data["content_types"]
        if "crawler" in data:
            crawler_data = data["crawler"]
            for key in ["data_dir", "index_file", "classifications_file", "max_retries", 
                        "classification_workers", "fetch_workers", "request_delay", "enable_tui"]:
                if key in crawler_data: setattr(config.crawler, key, crawler_data[key])
        if "memory" in data:
            mem_data = data["memory"]
            for key in ["output_dir", "topics_subdir", "links_subdir", "link_note_max_chars", 
                        "similarity_threshold", "embedding_model", "topic_index_db"]:
                if key in mem_data: setattr(config.memory, key, mem_data[key])
        if "search" in data:
            search_data = data["search"]
            for key in ["db_file", "default_mode"]:
                if key in search_data: setattr(config.search, key, search_data[key])
        if "default_input_file" in data: config.default_input_file = data["default_input_file"]
        return config
    
    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> "Config":
        if cls._instance is None: cls._instance = cls.load(config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

def get_config(config_path: Optional[Path] = None) -> Config:
    return Config.get_instance(config_path)

# --- Models ---

class ClassificationResult(BaseModel):
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
        if not v: raise ValueError("tags must be a non-empty list")
        return v

class LinkData(BaseModel):
    link: str
    id: str
    filename: Optional[str] = None
    status: str = "pending"
    content: Optional[str] = None
    classification: Optional[ClassificationResult] = None
    screenshot_filename: Optional[str] = None
    readable_filename: Optional[str] = None
    content_type: Optional[str] = None
    source_file_path: Optional[str] = None

    @field_validator("link")
    @classmethod
    def validate_url(cls, v: str) -> str:
        url_pattern = re.compile(r"^https?://", re.IGNORECASE)
        if not url_pattern.match(v): raise ValueError(f"Invalid URL format: {v}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "fetching", "fetch_complete", "classifying", "success", "failed"}
        if v not in allowed: raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v

class ProcessingStage(Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    FETCH_COMPLETE = "fetch_complete"
    CLASSIFYING = "classifying"
    SUCCESS = "success"
    FAILED = "failed"

class CrawlerConfig(BaseModel):
    data_dir: str = ".cache/dat"
    index_file: str = ".cache/index.json"
    classifications_file: str = ".cache/classifications.json"
    max_retries: int = 3
    classification_workers: int = 5
    fetch_workers: int = 5
    request_delay: float = 1.0
    enable_tui: bool = False
