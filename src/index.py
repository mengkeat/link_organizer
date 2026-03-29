"""
Link index and extraction logic.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from .core import get_logger

logger = get_logger("index")

@dataclass
class IndexEntry:
    link: str
    id: str
    filename: Optional[str] = None
    readable_filename: Optional[str] = None
    status: str = "pending"
    crawled_at: Optional[str] = None
    classification: Optional[Dict[str, Any]] = None
    screenshot_filename: Optional[str] = None
    memory_topic_id: Optional[str] = None
    memory_topic_file: Optional[str] = None
    memory_link_file: Optional[str] = None
    memory_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "link": self.link, "id": self.id, "filename": self.filename,
            "readable_filename": self.readable_filename, "status": self.status,
            "crawled_at": self.crawled_at, "screenshot_filename": self.screenshot_filename,
            "memory_topic_id": self.memory_topic_id, "memory_topic_file": self.memory_topic_file,
            "memory_link_file": self.memory_link_file, "memory_error": self.memory_error,
        }
        if self.classification: result["classification"] = self.classification
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexEntry":
        return cls(
            link=data.get("link", ""), id=data.get("id", ""),
            filename=data.get("filename"), readable_filename=data.get("readable_filename"),
            status=data.get("status", "pending"), crawled_at=data.get("crawled_at"),
            classification=data.get("classification"), screenshot_filename=data.get("screenshot_filename"),
            memory_topic_id=data.get("memory_topic_id"), memory_topic_file=data.get("memory_topic_file"),
            memory_link_file=data.get("memory_link_file"), memory_error=data.get("memory_error"),
        )

class LinkIndex:
    def __init__(self, index_file: Path = Path(".cache/index.json")):
        self.index_file = index_file
        self._entries: Dict[str, IndexEntry] = {}
        self._load()
    
    def _load(self):
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding='utf-8'))
                for item in data:
                    entry = IndexEntry.from_dict(item)
                    self._entries[entry.link] = entry
            except Exception as e:
                logger.warning("Failed to load index: %s", e)
    
    def save(self):
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        data = [entry.to_dict() for entry in self._entries.values()]
        self.index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def get(self, link: str) -> Optional[IndexEntry]: return self._entries.get(link)
    def add(self, entry: IndexEntry): self._entries[entry.link] = entry
    def remove(self, link: str): self._entries.pop(link, None)
    def get_all(self) -> List[IndexEntry]: return list(self._entries.values())
    
    def get_successful_links(self) -> Set[str]:
        return {e.link for e in self._entries.values() if e.status == "Success"}
    
    def find_new_links(self, links: List[str]) -> List[str]:
        existing = set(self._entries.keys())
        return [link for link in links if link not in existing]

    def search(self, query: str) -> List[IndexEntry]:
        query_lower = query.lower()
        results = []
        for entry in self._entries.values():
            if query_lower in entry.link.lower():
                results.append(entry)
                continue
            if entry.classification:
                if (query_lower in entry.classification.get('summary', '').lower() or 
                    query_lower in entry.classification.get('category', '').lower() or
                    any(query_lower in t.lower() for t in entry.classification.get('tags', []))):
                    results.append(entry)
        return results

class LinkExtractor:
    MD_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^\s)]+)\)")
    BARE_LINK_PATTERN = re.compile(r"(?<!\]\()(?<!\]\s)(https?://[^\s)]+)")

    @classmethod
    def extract_links_from_text(cls, content: str) -> list[str]:
        md_links = cls.MD_LINK_PATTERN.findall(content)
        bare_links = cls.BARE_LINK_PATTERN.findall(content)
        return list(dict.fromkeys(md_links + bare_links))

    @classmethod
    def extract_links_from_file(cls, filepath: str | Path) -> list[str]:
        path = Path(filepath)
        if not path.exists(): raise FileNotFoundError(f"File not found: {filepath}")
        content = path.read_text(encoding="utf-8")
        return cls.extract_links_from_text(content)

def extract_links_from_file(filepath: str | Path) -> list[str]:
    return LinkExtractor.extract_links_from_file(filepath)
