#!/usr/bin/env python3
"""
Tests for build_search_docs.py script.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

# Add parent directory to path to import the script
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.build_search_docs import (
    load_json_file, extract_title_from_url, merge_data_sources,
    validate_docs, write_search_data
)


def test_extract_title_from_url():
    """Test URL title extraction."""
    
    # Test with path components
    assert "how slow is select | vettabase.com" in extract_title_from_url("https://vettabase.com/blog/how-slow-is-select/")
    
    # Test with domain only
    assert extract_title_from_url("https://example.com/") == "example.com"
    
    # Test with www removal
    assert extract_title_from_url("https://www.example.com/") == "example.com"


def test_merge_data_sources():
    """Test merging of index and classification data."""
    
    # Sample index data
    index_data = [
        {
            "id": "test1",
            "link": "https://example.com/article1",
            "status": "Success",
            "classification": {
                "category": "Technology",
                "tags": ["web", "test"],
                "summary": "Test article"
            }
        },
        {
            "id": "test2", 
            "link": "https://example.com/article2",
            "status": "Failed"  # Should be skipped
        }
    ]
    
    # Sample classification data
    classifications_data = {
        "https://example.com/article3": {
            "category": "Science",
            "tags": ["research"],
            "summary": "Science article"
        }
    }
    
    docs = merge_data_sources(index_data, classifications_data)
    
    # Should only process successful items
    assert len(docs) == 1
    assert docs[0]["id"] == "test1"
    assert docs[0]["url"] == "https://example.com/article1"
    assert docs[0]["category"] == "Technology"
    assert "web" in docs[0]["tags"]
    assert "test" in docs[0]["tags"]
    assert "Technology" in docs[0]["tags"]  # Category should be added as tag


def test_validate_docs():
    """Test document validation."""
    
    # Valid documents
    valid_docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test",
            "summary": "Test summary",
            "tags": ["tag1", "tag2"]
        }
    ]
    
    assert validate_docs(valid_docs) == True
    
    # Invalid documents - missing field
    invalid_docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test"
            # Missing summary and tags
        }
    ]
    
    assert validate_docs(invalid_docs) == False
    
    # Empty documents
    assert validate_docs([]) == False


def test_write_search_data():
    """Test writing search data to JavaScript file."""
    
    docs = [
        {
            "id": "test1",
            "url": "https://example.com",
            "title": "Test Article",
            "summary": "A test article",
            "tags": ["test"]
        }
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "search-data.js"
        
        write_search_data(docs, output_path)
        
        # Check file exists
        assert output_path.exists()
        
        # Check file content
        content = output_path.read_text(encoding='utf-8')
        assert content.startswith("window.SEARCH_DATA = ")
        assert "test1" in content
        assert "Test Article" in content
        
        # Try to extract and validate JSON
        json_str = content.replace("window.SEARCH_DATA = ", "").rstrip(";")
        data = json.loads(json_str)
        
        assert "docs" in data
        assert "meta" in data
        assert len(data["docs"]) == 1
        assert data["docs"][0]["id"] == "test1"


def test_load_json_file():
    """Test JSON file loading with error handling."""
    
    # Test valid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "data"}, f)
        temp_path = Path(f.name)
    
    try:
        data = load_json_file(temp_path)
        assert data == {"test": "data"}
    finally:
        temp_path.unlink()
    
    # Test non-existent file
    try:
        load_json_file(Path("/nonexistent/file.json"))
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass


def run_integration_test():
    """Run an integration test with sample data."""
    
    # Create sample data files
    sample_index = [
        {
            "id": "sample1",
            "link": "https://example.com/test",
            "status": "Success",
            "classification": {
                "category": "Technology",
                "tags": ["web", "test"],
                "summary": "Sample test article for integration testing"
            }
        }
    ]
    
    sample_classifications = {
        "https://example.com/test": {
            "category": "Technology",
            "tags": ["integration"],
            "summary": "Additional classification data"
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write sample files
        index_file = temp_path / "index.json"
        classifications_file = temp_path / "classifications.json"
        output_file = temp_path / "generated_output" / "search-data.js"
        
        with open(index_file, 'w') as f:
            json.dump(sample_index, f)
        
        with open(classifications_file, 'w') as f:
            json.dump(sample_classifications, f)
        
        # Mock the file paths in the main function
        with mock.patch('scripts.build_search_docs.Path') as mock_path:
            mock_path.return_value.parent.parent = temp_path
            
            # Import and run main function
            from scripts.build_search_docs import main
            
            # This would run the full integration, but we'll just test components
            index_data = load_json_file(index_file)
            classifications_data = load_json_file(classifications_file)
            docs = merge_data_sources(index_data, classifications_data)
            
            assert len(docs) == 1
            assert validate_docs(docs)
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            write_search_data(docs, output_file)
            
            assert output_file.exists()


if __name__ == '__main__':
    """Run tests directly."""
    
    print("Running tests...")
    
    try:
        test_extract_title_from_url()
        print("✓ test_extract_title_from_url passed")
        
        test_merge_data_sources()
        print("✓ test_merge_data_sources passed")
        
        test_validate_docs()
        print("✓ test_validate_docs passed")
        
        test_write_search_data()
        print("✓ test_write_search_data passed")
        
        test_load_json_file()
        print("✓ test_load_json_file passed")
        
        run_integration_test()
        print("✓ integration test passed")
        
        print("\nAll tests passed! ✓")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)