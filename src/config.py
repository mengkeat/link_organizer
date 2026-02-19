"""
Configuration management for link organizer
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import yaml


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
    data_dir: str = "dat"
    index_file: str = "index.json"
    classifications_file: str = "classifications.json"
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
    link_note_max_chars: int = 120000
    similarity_threshold: float = 0.75
    embedding_model: str = "openrouter/openai/text-embedding-3-small"


@dataclass
class Config:
    """Main configuration class for link organizer"""
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    crawler: CrawlerConfigSettings = field(default_factory=CrawlerConfigSettings)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    default_input_file: str = "links.md"
    
    _instance: Optional["Config"] = field(default=None, init=False, repr=False)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from YAML file or use defaults.
        
        Args:
            config_path: Path to config file. Defaults to config.yaml in project root.
            
        Returns:
            Config instance with loaded or default settings.
        """
        if config_path is None:
            config_path = Path("config.yaml")
        
        if not config_path.exists():
            return cls()
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        config = cls()
        
        if "classification" in data:
            class_data = data["classification"]
            if "categories" in class_data:
                config.classification.categories = class_data["categories"]
            if "content_types" in class_data:
                config.classification.content_types = class_data["content_types"]
        
        if "crawler" in data:
            crawler_data = data["crawler"]
            for key in ["data_dir", "index_file", "classifications_file", 
                        "max_retries", "classification_workers", "fetch_workers",
                        "request_delay", "enable_tui"]:
                if key in crawler_data:
                    setattr(config.crawler, key, crawler_data[key])
        
        if "memory" in data:
            mem_data = data["memory"]
            for key in [
                "output_dir",
                "topics_subdir",
                "links_subdir",
                "link_note_max_chars",
                "similarity_threshold",
                "embedding_model",
            ]:
                if key in mem_data:
                    setattr(config.memory, key, mem_data[key])
        
        if "default_input_file" in data:
            config.default_input_file = data["default_input_file"]
        
        return config
    
    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> "Config":
        """Get singleton instance of Config.
        
        Args:
            config_path: Path to config file (only used on first call).
            
        Returns:
            Singleton Config instance.
        """
        if cls._instance is None:
            cls._instance = cls.load(config_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None


def get_config(config_path: Optional[Path] = None) -> Config:
    """Convenience function to get config singleton.
    
    Args:
        config_path: Path to config file (only used on first call).
        
    Returns:
        Config singleton instance.
    """
    return Config.get_instance(config_path)
