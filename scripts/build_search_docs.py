#!/usr/bin/env python3
"""
Build search documents from the database.

This script processes link data and creates a lightweight search data bundle
suitable for client-side search in the browser.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

from src.database import db


def extract_title_from_url(url: str) -> str:
    """Extract a basic title from URL if no better title available."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if path_parts:
        # Use the last meaningful path component
        title_part = path_parts[-1].replace('-', ' ').replace('_', ' ')
        if title_part and not title_part.endswith('.html'):
            return f"{title_part} | {domain}"
    
    return domain

def create_search_documents(links) -> List[Dict[str, Any]]:
    """
    Create search documents from a list of LinkData objects.
    """
    docs = []
    for link_data in links:
        if not link_data.classification:
            continue

        classification = link_data.classification

        summary = classification.summary or ''
        title = extract_title_from_url(link_data.link)

        tags = classification.tags or []
        if isinstance(tags, str):
            tags = [tags]

        category = classification.category or ''
        subcategory = classification.subcategory or ''

        all_tags = tags.copy()
        if category:
            all_tags.append(category)
        if subcategory and subcategory != category:
            all_tags.append(subcategory)

        key_topics = classification.key_topics or []
        if isinstance(key_topics, list):
            all_tags.extend(key_topics)

        all_tags = list(set(tag.strip() for tag in all_tags if tag and tag.strip()))

        doc = {
            'id': link_data.id,
            'url': link_data.link,
            'title': title,
            'summary': summary,
            'tags': all_tags,
            'category': category,
            'subcategory': subcategory,
            'content_type': classification.content_type or 'article',
            'difficulty': classification.difficulty or 'unknown',
            'quality_score': classification.quality_score or 0,
            'confidence': classification.confidence or 0.0
        }
        docs.append(doc)
    return docs

def validate_docs(docs: List[Dict]) -> bool:
    """Validate document structure and content."""
    if not docs:
        print("Error: No valid documents found")
        return False
    
    required_fields = ['id', 'url', 'title', 'summary', 'tags']
    
    for i, doc in enumerate(docs):
        for field in required_fields:
            if field not in doc:
                print(f"Error: Document {i} missing required field: {field}")
                return False
        
        if not isinstance(doc['tags'], list):
            print(f"Error: Document {i} tags must be a list")
            return False
    
    print(f"Validated {len(docs)} documents successfully")
    return True

def write_search_data(docs: List[Dict], output_path: Path) -> None:
    """Write search data to JavaScript file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        meta = {
            'total_docs': len(docs),
            'generated_at': '',  # Will be set by JavaScript Date
            'version': '1.0.0'
        }
        
        search_data = {
            'docs': docs,
            'meta': meta
        }
        
        js_content = f"window.SEARCH_DATA = {json.dumps(search_data, indent=2, ensure_ascii=False)};"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"Successfully wrote search data to {output_path}")
        print(f"Total documents: {len(docs)}")
        
        size_bytes = len(js_content.encode('utf-8'))
        size_kb = size_bytes / 1024
        print(f"File size: {size_kb:.1f} KB")
        
        if size_kb > 100:
            print("Note: File size >100KB - consider compression for production")
        
    except Exception as e:
        print(f"Error writing search data: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    output_file = repo_root / 'generated_output' / 'search-data.js'
    
    print("Building search documents from the database...")
    print(f"Output file: {output_file}")
    
    # Get all links with classifications
    all_links = db.get_all_links()
    classified_links = [link for link in all_links if link.classification is not None]
    
    print(f"Found {len(classified_links)} classified links in the database.")

    docs = create_search_documents(classified_links)
    
    if not validate_docs(docs):
        sys.exit(1)
    
    write_search_data(docs, output_file)
    
    public_file = repo_root / 'public' / 'search-data.js'
    try:
        import shutil
        shutil.copy2(output_file, public_file)
        print(f"Copied search data to {public_file}")
    except Exception as e:
        print(f"Warning: Could not copy to public directory: {e}")
    
    print("\nBuild completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
