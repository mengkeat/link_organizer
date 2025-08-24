# Browser Search Index

This system creates a browser-embeddable search index from your link collection data, allowing fast client-side search without server dependencies.

## Quick Start

1. **Build search data**: 
   ```bash
   python scripts/build_search_docs.py
   ```

2. **Serve demo**:
   ```bash
   cd public && python -m http.server 8000
   ```

3. **Open browser**: Visit `http://localhost:8000/search.html`

## How It Works

The system processes two input files:
- `index.json` - Main link data with metadata and classifications
- `classifications.json` - Additional classification data (optional)

It creates `generated_output/search-data.js` containing lightweight document records optimized for client-side search.

## Search Features

- **Full-text search** across titles, summaries, and tags
- **Category filtering** by content type, difficulty, and category
- **Tag-based search** with AI-generated classifications
- **Web Worker support** for responsive UI with large datasets
- **Fuzzy matching** and prefix search for better results

## File Structure

```
├── scripts/
│   └── build_search_docs.py     # Python build script
├── public/
│   ├── search.html              # Search interface
│   └── search-worker.js         # Web Worker for search
├── generated_output/
│   └── search-data.js           # Generated search data
└── tests/
    └── test_build_search_docs.py # Unit tests
```

## Performance Guidelines

- **< 5k docs**: Client builds index at runtime (current approach)
- **5k-50k docs**: Consider pre-built serialized indexes with compression
- **> 50k docs**: Recommend server-side search (Typesense, Meilisearch)

## Data Format

Each search document contains:
```json
{
  "id": "unique-hash-id",
  "url": "https://example.com/article",
  "title": "Article Title",
  "summary": "Brief content summary",
  "tags": ["tag1", "tag2", "category"],
  "category": "Technology",
  "subcategory": "Programming",
  "content_type": "article",
  "difficulty": "intermediate",
  "quality_score": 7,
  "confidence": 0.8
}
```

## Compression & Production

For production deployment:

1. **Enable compression**: Configure your web server to serve `.js` files with gzip/brotli compression
2. **Set headers**: 
   ```
   Content-Type: application/javascript
   Cache-Control: public, max-age=3600
   ```
3. **Monitor size**: Current data generates ~50KB uncompressed, ~15KB gzipped

## Testing

Run the test suite:
```bash
python tests/test_build_search_docs.py
```

Or use pytest:
```bash
pytest tests/test_build_search_docs.py -v
```

## Troubleshooting

**"Search data not loaded" error**: Run the build script first:
```bash
python scripts/build_search_docs.py
```

**Worker not supported**: The interface falls back to main-thread search automatically. Modern browsers support Web Workers.

**Slow search**: For datasets >10MB, consider implementing server-side search or data pagination.