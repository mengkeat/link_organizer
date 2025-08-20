#!/usr/bin/env python3
"""
Enhanced Link Crawler with AI Classification
Extends the original crawler with automatic classification capabilities
"""

import os
import hashlib
import json
import asyncio
from urllib.parse import urlparse
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from get_count_links import extract_links_from_file
from link_classifier import LinkClassifier

LINKS_MD = "links.md"
DATA_DIR = "dat"
INDEX_JSON = "index.json"
CLASSIFICATIONS_JSON = "classifications.json"

def hash_link(link):
    return hashlib.sha256(link.encode("utf-8")).hexdigest()

def is_pdf(url):
    return url.lower().endswith(".pdf") or "pdf" in urlparse(url).path.lower()

async def fetch_and_convert(crawler, url):
    if is_pdf(url):
        # Download PDF directly
        import requests

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content, "pdf"
    # Use crawler4ai for HTML/Markdown
    config = CrawlerRunConfig(
        css_selector=None,  # Use default or customize as needed
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_domains=[],
        exclude_external_images=True,
        cache_mode=CacheMode.BYPASS,
    )
    result = await crawler.arun(url=url, config=config)
    if result.success:
        return result.markdown, "md"
    else:
        return "", None

async def process_link_enhanced(crawler, classifier, link, idx, total):
    """Enhanced link processing with classification"""
    id_ = hash_link(link)
    print(f"[{idx+1}/{total}] Processing: {link} with hash {id_}")

    try:
        # Fetch content
        content, typ = await fetch_and_convert(crawler, link)

        if not content:
            return {"link": link, "id": id_, "filename": None, "status": "Failed: No content"}

        # Save content to file
        fname = f"{id_}.{typ}"
        fpath = os.path.join(DATA_DIR, fname)
        mode = "wb" if typ == "pdf" else "w"
        with open(fpath, mode, encoding=None if typ == "pdf" else "utf-8") as f:
            f.write(content)

        # Classify content
        print(f"[{idx+1}/{total}] Classifying content...")
        title = link.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
        classification = await classifier.classify_content(link, title, content)

        # Create enhanced result
        result = {
            "link": link,
            "id": id_,
            "filename": fname,
            "status": "Success",
            "classification": {
                "category": classification.category,
                "subcategory": classification.subcategory,
                "tags": classification.tags,
                "summary": classification.summary,
                "confidence": classification.confidence,
                "content_type": classification.content_type,
                "difficulty": classification.difficulty,
                "quality_score": classification.quality_score,
                "key_topics": classification.key_topics,
                "target_audience": classification.target_audience
            }
        }

        print(f"[{idx+1}/{total}] Success: {link} -> {fname} ({classification.category})")
        return result

    except Exception as e:
        print(f"[{idx+1}/{total}] Failed: {link}: {e}")
        return {"link": link, "id": id_, "filename": None, "status": f"Failed: {e}"}

async def main_enhanced():
    """Enhanced main function with classification"""
    os.makedirs(DATA_DIR, exist_ok=True)
    links = extract_links_from_file(LINKS_MD)
    total = len(links)
    print(f"Found {total} links in {LINKS_MD}")

    # Initialize classifier
    classifier = LinkClassifier()

    index = []
    classifications = {}

    async with AsyncWebCrawler() as crawler:
        # Process links concurrently with classification
        sem = asyncio.Semaphore(5)  # Reduced concurrency for API rate limits

        async def sem_task(idx, link):
            async with sem:
                return await process_link_enhanced(crawler, classifier, link, idx, total)

        tasks = [sem_task(idx, link) for idx, link in enumerate(links)]
        for fut in asyncio.as_completed(tasks):
            result = await fut
            index.append(result)

            # Store classification separately
            if "classification" in result:
                classifications[result["link"]] = result["classification"]

            print(f"Processed {len(index)}/{total} links")

    # Save index
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    # Save classifications
    with open(CLASSIFICATIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(classifications, f, indent=2, ensure_ascii=False)

    print(f"\nEnhanced crawling complete!")
    print(f"Index saved to {INDEX_JSON}")
    print(f"Classifications saved to {CLASSIFICATIONS_JSON}")

def main():
    """Original main function for compatibility"""
    asyncio.run(main_enhanced())

if __name__ == "__main__":
    main()
