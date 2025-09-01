"""
Database operations using direct sqlite3 connections for the link organizer.
"""
import sqlite3
import json
import threading
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from pathlib import Path

from .models import LinkData, ClassificationResult


class Database:
    """Database manager for link organizer using direct sqlite3 connections"""
    
    def __init__(self, db_path: str = "links.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
    
    def _init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create link_data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_data (
                    id TEXT PRIMARY KEY,
                    link TEXT UNIQUE NOT NULL,
                    filename TEXT,
                    status TEXT DEFAULT 'pending',
                    content TEXT,
                    screenshot_filename TEXT,
                    embedding TEXT
                )
            """)
            
            # Create classification_results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classification_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_data_id TEXT NOT NULL,
                    category TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    summary TEXT,
                    confidence REAL,
                    content_type TEXT,
                    difficulty TEXT,
                    quality_score INTEGER,
                    key_topics TEXT,
                    target_audience TEXT,
                    FOREIGN KEY (link_data_id) REFERENCES link_data(id)
                )
            """)
            
            # Create collections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT
                )
            """)
            
            # Create link_collections junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_collections (
                    link_id TEXT NOT NULL,
                    collection_id INTEGER NOT NULL,
                    PRIMARY KEY (link_id, collection_id),
                    FOREIGN KEY (link_id) REFERENCES link_data(id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_data_link ON link_data(link)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_data_status ON link_data(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_link_id ON classification_results(link_data_id)")
    
    def save_link_data(self, link_data: LinkData) -> None:
        """Save or update link data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO link_data 
                (id, link, filename, status, content, screenshot_filename)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                link_data.id,
                link_data.link,
                link_data.filename,
                link_data.status,
                link_data.content,
                link_data.screenshot_filename
            ))
    
    def get_link_data(self, link_id: str) -> Optional[LinkData]:
        """Retrieve link data by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM link_data WHERE id = ?", (link_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            # Get classification if it exists
            classification = self.get_classification(link_id)
            
            return LinkData(
                id=row['id'],
                link=row['link'],
                filename=row['filename'],
                status=row['status'],
                content=row['content'],
                screenshot_filename=row['screenshot_filename'],
                classification=classification
            )
    
    def get_link_by_url(self, url: str) -> Optional[LinkData]:
        """Retrieve link data by URL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM link_data WHERE link = ?", (url,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            # Get classification if it exists
            classification = self.get_classification(row['id'])
            
            return LinkData(
                id=row['id'],
                link=row['link'],
                filename=row['filename'],
                status=row['status'],
                content=row['content'],
                screenshot_filename=row['screenshot_filename'],
                classification=classification
            )
    
    def save_classification(self, link_id: str, classification: ClassificationResult) -> None:
        """Save classification result for a link"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO classification_results 
                (link_data_id, category, subcategory, tags, summary, confidence, 
                 content_type, difficulty, quality_score, key_topics, target_audience)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link_id,
                classification.category,
                classification.subcategory,
                json.dumps(classification.tags),
                classification.summary,
                classification.confidence,
                classification.content_type,
                classification.difficulty,
                classification.quality_score,
                json.dumps(classification.key_topics),
                classification.target_audience
            ))
    
    def get_classification(self, link_id: str) -> Optional[ClassificationResult]:
        """Get classification result for a link"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM classification_results WHERE link_data_id = ?
            """, (link_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return ClassificationResult(
                category=row['category'] or "",
                subcategory=row['subcategory'] or "",
                tags=json.loads(row['tags']) if row['tags'] else [],
                summary=row['summary'] or "",
                confidence=row['confidence'] or 0.0,
                content_type=row['content_type'] or "",
                difficulty=row['difficulty'] or "",
                quality_score=row['quality_score'] or 0,
                key_topics=json.loads(row['key_topics']) if row['key_topics'] else [],
                target_audience=row['target_audience'] or ""
            )
    
    def get_all_links(self) -> List[LinkData]:
        """Get all links with their classifications"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM link_data")
            rows = cursor.fetchall()
            
            links = []
            for row in rows:
                classification = self.get_classification(row['id'])
                links.append(LinkData(
                    id=row['id'],
                    link=row['link'],
                    filename=row['filename'],
                    status=row['status'],
                    content=row['content'],
                    screenshot_filename=row['screenshot_filename'],
                    classification=classification
                ))
            
            return links
    
    def get_links_by_status(self, status: str) -> List[LinkData]:
        """Get all links with a specific status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM link_data WHERE status = ?", (status,))
            rows = cursor.fetchall()
            
            links = []
            for row in rows:
                classification = self.get_classification(row['id'])
                links.append(LinkData(
                    id=row['id'],
                    link=row['link'],
                    filename=row['filename'],
                    status=row['status'],
                    content=row['content'],
                    screenshot_filename=row['screenshot_filename'],
                    classification=classification
                ))
            
            return links
    
    def update_link_status(self, link_id: str, status: str) -> None:
        """Update the status of a link"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE link_data SET status = ? WHERE id = ?
            """, (status, link_id))
    
    def create_collection(self, name: str, description: str = "") -> int:
        """Create a new collection"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collections (name, description) VALUES (?, ?)
            """, (name, description))
            return cursor.lastrowid
    
    def add_link_to_collection(self, link_id: str, collection_id: int) -> None:
        """Add a link to a collection"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO link_collections (link_id, collection_id) 
                VALUES (?, ?)
            """, (link_id, collection_id))
    
    def get_collection_links(self, collection_id: int) -> List[LinkData]:
        """Get all links in a collection"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ld.* FROM link_data ld
                JOIN link_collections lc ON ld.id = lc.link_id
                WHERE lc.collection_id = ?
            """, (collection_id,))
            rows = cursor.fetchall()
            
            links = []
            for row in rows:
                classification = self.get_classification(row['id'])
                links.append(LinkData(
                    id=row['id'],
                    link=row['link'],
                    filename=row['filename'],
                    status=row['status'],
                    content=row['content'],
                    screenshot_filename=row['screenshot_filename'],
                    classification=classification
                ))
            
            return links
    
    def get_all_collections(self) -> List[Tuple[int, str, str]]:
        """Get all collections"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description FROM collections")
            return [(row['id'], row['name'], row['description']) for row in cursor.fetchall()]
    
    def close(self):
        """Close the database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


# Global database instance
db = Database()