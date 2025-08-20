# Link Classification System

This system uses LiteLLM with OpenRouter to automatically classify, tag, and summarize web content in your link organizer.

## Features

- **Automatic Classification**: Categorizes links using AI
- **Smart Tagging**: Generates relevant tags for better organization
- **Content Summarization**: Creates concise summaries
- **Multi-format Support**: Works with Markdown and PDF files
- **OpenRouter Integration**: Supports multiple AI models through unified API
- **Batch Processing**: Classify all existing links at once

## Setup

### 1. Get OpenRouter API Key
1. Visit [OpenRouter.ai](https://openrouter.ai/keys)
2. Sign up and generate an API key
3. Copy the key

### 2. Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
OPENROUTER_API_KEY=your_actual_api_key_here
```

### 3. Install Dependencies
```bash
uv pip install litellm PyPDF2 python-dotenv
```

## Usage

### Test the System
```bash
# Test with a single example
python test_classification.py --single

# Interactive testing
python test_classification.py --interactive

# Classify existing links (first 5 for testing)
python test_classification.py --existing --limit 5
```

### Classify All Existing Links
```bash
# Classify all links in your index.json
python test_classification.py --existing --output classifications.json
```

### Use in Your Code
```python
from link_classifier import LinkClassifier
import asyncio

async def main():
    classifier = LinkClassifier()

    result = await classifier.classify_content(
        url="https://example.com",
        title="Example Article",
        content="Your article content here..."
    )

    print(f"Category: {result.category}")
    print(f"Tags: {result.tags}")
    print(f"Summary: {result.summary}")

asyncio.run(main())
```

## Integration with Existing System

### Option 1: Extend Current Crawler
Modify `crawl_links.py` to automatically classify new links:

```python
# In your crawl_links.py, after fetching content:
from link_classifier import LinkClassifier

classifier = LinkClassifier()

# After saving content to file
result = await classifier.classify_content(link, title, content)

# Save classification alongside content
classification_data = {
    "link": link,
    "id": id_,
    "filename": fname,
    "classification": {
        "category": result.category,
        "tags": result.tags,
        "summary": result.summary,
        # ... other fields
    }
}
```

### Option 2: Batch Process Existing Links
```bash
# Classify all existing links
python test_classification.py --existing

# This creates classifications.json with all results
```

### Option 3: Real-time Classification
Add a new script for real-time classification of individual links:

```python
# classify_link.py
import asyncio
from link_classifier import LinkClassifier

async def classify_single_link(link_url):
    classifier = LinkClassifier()
    # You'll need to fetch content first
    content = fetch_content_from_url(link_url)
    result = await classifier.classify_content(link_url, "", content)
    return result

# Usage
result = asyncio.run(classify_single_link("https://example.com"))
```

## Classification Output

Each classification returns:

```json
{
  "category": "AI/ML",
  "subcategory": "Machine Learning",
  "tags": ["neural networks", "deep learning", "python", "tensorflow"],
  "summary": "Comprehensive guide covering neural networks and deep learning techniques...",
  "confidence": 0.92,
  "content_type": "tutorial",
  "difficulty": "intermediate",
  "quality_score": 8,
  "key_topics": ["neural networks", "backpropagation", "optimization"],
  "target_audience": "data scientists and ML engineers"
}
```

## Configuration Options

### Change Models
```python
# Use Claude instead of GPT-4
classifier = LinkClassifier("openrouter/anthropic/claude-3-sonnet")

# Use Llama
classifier = LinkClassifier("openrouter/meta-llama/llama-3-70b-instruct")
```

### Available Categories
- Technology
- Science
- AI/ML
- Programming
- Research
- Tutorial
- News
- Blog
- Documentation
- Business
- Design
- Security
- Data Science
- Web Development

### Content Types
- tutorial
- guide
- documentation
- research_paper
- blog_post
- news_article
- reference
- course
- tool

## Next Steps

1. **Set up your API key** in `.env`
2. **Test the system** with existing links
3. **Integrate with your crawler** for automatic classification
4. **Add search functionality** based on classifications
5. **Consider database storage** for better querying

## Troubleshooting

### API Key Issues
- Ensure `OPENROUTER_API_KEY` is set in `.env`
- Check that your OpenRouter account has credits
- Verify the API key has the right permissions

### Rate Limiting
- OpenRouter has rate limits based on your plan
- The system includes delays between requests
- Consider upgrading your OpenRouter plan for faster processing

### Content Extraction Issues
- PDF extraction requires PyPDF2
- Some PDFs may have encoding issues
- Markdown files should be UTF-8 encoded

## Cost Estimation

Based on OpenRouter pricing (as of 2024):
- GPT-4: ~$0.01 per classification
- Claude-3: ~$0.005 per classification
- Llama-3: ~$0.001 per classification

For 1000 links: $10-$1 depending on model choice.
