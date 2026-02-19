"""
Link index management with incremental sync support
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass


@dataclass
class IndexEntry:
    """Represents an entry in the link index"""
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
            "link": self.link,
            "id": self.id,
            "filename": self.filename,
            "readable_filename": self.readable_filename,
            "status": self.status,
            "crawled_at": self.crawled_at,
            "screenshot_filename": self.screenshot_filename,
            "memory_topic_id": self.memory_topic_id,
            "memory_topic_file": self.memory_topic_file,
            "memory_link_file": self.memory_link_file,
            "memory_error": self.memory_error,
        }
        if self.classification:
            result["classification"] = self.classification
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexEntry":
        return cls(
            link=data.get("link", ""),
            id=data.get("id", ""),
            filename=data.get("filename"),
            readable_filename=data.get("readable_filename"),
            status=data.get("status", "pending"),
            crawled_at=data.get("crawled_at"),
            classification=data.get("classification"),
            screenshot_filename=data.get("screenshot_filename"),
            memory_topic_id=data.get("memory_topic_id"),
            memory_topic_file=data.get("memory_topic_file"),
            memory_link_file=data.get("memory_link_file"),
            memory_error=data.get("memory_error"),
        )


class LinkIndex:
    """Manages link index with support for incremental operations"""
    
    def __init__(self, index_file: Path = Path("index.json")):
        self.index_file = index_file
        self._entries: Dict[str, IndexEntry] = {}
        self._load()
    
    def _load(self):
        """Load existing index from file."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding='utf-8'))
                for item in data:
                    entry = IndexEntry.from_dict(item)
                    self._entries[entry.link] = entry
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load index: {e}")
    
    def save(self):
        """Save index to file."""
        data = [entry.to_dict() for entry in self._entries.values()]
        self.index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def get(self, link: str) -> Optional[IndexEntry]:
        """Get entry for a specific link."""
        return self._entries.get(link)
    
    def add(self, entry: IndexEntry):
        """Add or update an entry."""
        self._entries[entry.link] = entry
    
    def remove(self, link: str):
        """Remove an entry."""
        self._entries.pop(link, None)
    
    def get_all(self) -> List[IndexEntry]:
        """Get all entries."""
        return list(self._entries.values())
    
    def get_by_status(self, status: str) -> List[IndexEntry]:
        """Get entries by status."""
        return [e for e in self._entries.values() if e.status == status]
    
    def get_by_category(self, category: str) -> List[IndexEntry]:
        """Get entries by category."""
        return [
            e for e in self._entries.values()
            if e.classification and e.classification.get('category') == category
        ]
    
    def get_existing_links(self) -> Set[str]:
        """Get set of all links in index."""
        return set(self._entries.keys())
    
    def get_successful_links(self) -> Set[str]:
        """Get set of successfully processed links."""
        return {e.link for e in self._entries.values() if e.status == "Success"}
    
    def get_failed_links(self) -> Set[str]:
        """Get set of failed links."""
        return {e.link for e in self._entries.values() if e.status.startswith("Failed")}
    
    def get_pending_links(self) -> Set[str]:
        """Get set of pending links."""
        return {e.link for e in self._entries.values() if e.status == "pending"}
    
    def find_new_links(self, links: List[str]) -> List[str]:
        """Find links that are not in the index."""
        existing = self.get_existing_links()
        return [link for link in links if link not in existing]
    
    def find_links_to_retry(self) -> List[str]:
        """Find failed links that could be retried."""
        return list(self.get_failed_links())
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the index."""
        stats = {
            "total": len(self._entries),
            "success": 0,
            "failed": 0,
            "pending": 0
        }
        
        categories = {}
        for entry in self._entries.values():
            if entry.status == "Success":
                stats["success"] += 1
            elif entry.status.startswith("Failed"):
                stats["failed"] += 1
            else:
                stats["pending"] += 1
            
            if entry.classification:
                cat = entry.classification.get('category', 'Uncategorized')
                categories[cat] = categories.get(cat, 0) + 1
        
        stats["categories"] = categories
        return stats
    
    def search(self, query: str) -> List[IndexEntry]:
        """Search entries by URL or classification content."""
        query_lower = query.lower()
        results = []
        
        for entry in self._entries.values():
            # Search in URL
            if query_lower in entry.link.lower():
                results.append(entry)
                continue
            
            # Search in classification
            if entry.classification:
                summary = entry.classification.get('summary', '').lower()
                tags = [t.lower() for t in entry.classification.get('tags', [])]
                category = entry.classification.get('category', '').lower()
                
                if (query_lower in summary or 
                    query_lower in category or
                    any(query_lower in tag for tag in tags)):
                    results.append(entry)
        
        return results
    
    def list_categories(self) -> List[str]:
        """List all unique categories."""
        categories = set()
        for entry in self._entries.values():
            if entry.classification:
                categories.add(entry.classification.get('category', 'Uncategorized'))
        return sorted(categories)
    
    def list_tags(self) -> List[str]:
        """List all unique tags."""
        tags = set()
        for entry in self._entries.values():
            if entry.classification:
                tags.update(entry.classification.get('tags', []))
        return sorted(tags)
