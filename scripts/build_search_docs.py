#!/usr/bin/env python3
"""
Build search documents from index.json and classifications.json files.

This script processes link data and creates a lightweight search data bundle
suitable for client-side search in the browser.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse


def load_json_file(filepath: Path) -> Any:
    """Load and parse a JSON file with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)


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


def merge_data_sources(index_data: List[Dict], classifications_data: Dict[str, Dict]) -> List[Dict]:
    """
    Merge index.json and classifications.json into unified document records.
    
    Args:
        index_data: List of link records from index.json
        classifications_data: Dict mapping URLs to classification data
    
    Returns:
        List of merged document records
    """
    docs = []
    seen_ids = set()
    
    for item in index_data:
        # Skip failed items
        if item.get('status') != 'Success':
            continue
            
        link_id = item.get('id')
        if not link_id:
            continue
            
        # Check for duplicate IDs
        if link_id in seen_ids:
            print(f"Warning: Duplicate ID found: {link_id}")
            continue
        seen_ids.add(link_id)
        
        url = item.get('link', '')
        if not url:
            continue
        
        # Get classification data (try both embedded and separate file)
        classification = item.get('classification') or classifications_data.get(url, {})
        
        # Extract title - prefer from summary or generate from URL
        summary = classification.get('summary', '')
        title = extract_title_from_url(url)
        
        # Clean and prepare tags
        tags = classification.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        
        # Add category and subcategory as searchable tags
        category = classification.get('category', '')
        subcategory = classification.get('subcategory', '')
        
        all_tags = tags.copy()
        if category:
            all_tags.append(category)
        if subcategory and subcategory != category:
            all_tags.append(subcategory)
            
        # Add key topics as tags
        key_topics = classification.get('key_topics', [])
        if isinstance(key_topics, list):
            all_tags.extend(key_topics)
        
        # Remove duplicates and normalize
        all_tags = list(set(tag.strip() for tag in all_tags if tag and tag.strip()))
        
        doc = {
            'id': link_id,
            'url': url,
            'title': title,
            'summary': summary,
            'tags': all_tags,
            'category': category,
            'subcategory': subcategory,
            'content_type': classification.get('content_type', 'article'),
            'difficulty': classification.get('difficulty', 'unknown'),
            'quality_score': classification.get('quality_score', 0),
            'confidence': classification.get('confidence', 0.0)
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
        
        # Validate field types
        if not isinstance(doc['tags'], list):
            print(f"Error: Document {i} tags must be a list")
            return False
    
    print(f"Validated {len(docs)} documents successfully")
    return True


def write_search_data(docs: List[Dict], output_path: Path) -> None:
    """Write search data to JavaScript file."""
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        meta = {
            'total_docs': len(docs),
            'generated_at': '',  # Will be set by JavaScript Date
            'version': '1.0.0'
        }
        
        search_data = {
            'docs': docs,
            'meta': meta
        }
        
        # Write as JavaScript with global assignment
        js_content = f"window.SEARCH_DATA = {json.dumps(search_data, indent=2, ensure_ascii=False)};"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"Successfully wrote search data to {output_path}")
        print(f"Total documents: {len(docs)}")
        
        # Calculate approximate file size
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
    # Define file paths
    repo_root = Path(__file__).parent.parent
    index_file = repo_root / 'index.json'
    
    # Try both possible classification file names
    classifications_file = repo_root / 'classifications.json'
    if not classifications_file.exists():
        classifications_file = repo_root / 'classification_links.json'
    
    output_file = repo_root / 'generated_output' / 'search-data.js'
    
    print("Building search documents...")
    print(f"Input files:")
    print(f"  - Index: {index_file}")
    print(f"  - Classifications: {classifications_file}")
    print(f"Output file: {output_file}")
    
    # Load input data
    print("\nLoading input files...")
    index_data = load_json_file(index_file)
    
    classifications_data = {}
    if classifications_file.exists():
        classifications_data = load_json_file(classifications_file)
    else:
        print("Warning: No classifications file found, using embedded data only")
    
    # Merge and process data
    print("Processing and merging data...")
    docs = merge_data_sources(index_data, classifications_data)
    
    # Validate output
    if not validate_docs(docs):
        sys.exit(1)
    
    # Write output
    print("Writing search data...")
    write_search_data(docs, output_file)
    
    # Copy to public directory for web serving
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