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
MAX_RETRIES = 3  # Max retries for classification
CLASSIFICATION_WORKERS = 5  # Number of concurrent classification tasks
FETCH_WORKERS = 5 # Number of concurrent fetch tasks

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

async def fetch_link_content(crawler, link, idx, total):
    """Fetches content for a link and prepares it for classification."""
    id_ = hash_link(link)
    print(f"[{idx+1}/{total}] Fetching: {link}")
    try:
        content, typ = await fetch_and_convert(crawler, link)
        if not content:
            return {"link": link, "id": id_, "filename": None, "status": "Failed: No content"}

        fname = f"{id_}.{typ}"
        fpath = os.path.join(DATA_DIR, fname)
        mode = "wb" if typ == "pdf" else "w"
        with open(fpath, mode, encoding=None if typ == "pdf" else "utf-8") as f:
            f.write(content)

        return {"link": link, "id": id_, "filename": fname, "content": content, "status": "Fetched"}
    except Exception as e:
        print(f"[{idx+1}/{total}] Failed to fetch {link}: {e}")
        return {"link": link, "id": id_, "filename": None, "status": f"Failed: {e}"}

async def classification_worker(classifier, queue, results, failed_queue):
    """Worker that processes classification tasks from a queue."""
    while True:
        try:
            task = await queue.get()
            if task is None:
                break

            link = task["link"]
            content = task["content"]
            retries = task.get("retries", 0)

            print(f"Classifying: {link} (attempt {retries + 1})")

            try:
                title = link.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
                classification = await classifier.classify_content(link, title, content)

                result = {
                    "link": link,
                    "id": task["id"],
                    "filename": task["filename"],
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
                        "target_audience": classification.target_audience,
                    },
                }
                results.append(result)
                print(f"Success: {link} -> {task['filename']} ({classification.category})")
            except Exception as e:
                print(f"Classification failed for {link}: {e}")
                if retries < MAX_RETRIES:
                    task["retries"] = retries + 1
                    await queue.put(task)
                    print(f"Re-queued {link} for retry.")
                else:
                    print(f"Max retries reached for {link}. Marking as failed.")
                    failed_result = {
                        "link": link,
                        "id": task["id"],
                        "filename": task["filename"],
                        "status": f"Failed: Max retries exceeded. Last error: {e}",
                    }
                    failed_queue.put_nowait(failed_result)
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            break


async def fetch_worker(crawler, in_queue, out_queue, results_list, total):
    while True:
        try:
            idx, link = await in_queue.get()
            fetched_data = await fetch_link_content(crawler, link, idx, total)
            if fetched_data and fetched_data.get("content"):
                await out_queue.put(fetched_data)
            else:
                results_list.append(fetched_data)
            in_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Log error, not much else to do
            print(f"Error in fetch worker for link {link}: {e}")
            in_queue.task_done()


async def main_enhanced():
    """Enhanced main function with classification and retry queue"""
    os.makedirs(DATA_DIR, exist_ok=True)
    links = extract_links_from_file(LINKS_MD)
    total = len(links)
    print(f"Found {total} links in {LINKS_MD}")

    classifier = LinkClassifier()
    
    fetch_queue = asyncio.Queue()
    classification_queue = asyncio.Queue()
    results = []
    failed_classifications = asyncio.Queue()

    for idx, link in enumerate(links):
        await fetch_queue.put((idx, link))

    # Start classification workers
    classification_workers = [
        asyncio.create_task(classification_worker(classifier, classification_queue, results, failed_classifications))
        for _ in range(CLASSIFICATION_WORKERS)
    ]

    async with AsyncWebCrawler() as crawler:
        # Start fetch workers
        fetch_workers = [
            asyncio.create_task(fetch_worker(crawler, fetch_queue, classification_queue, results, total))
            for _ in range(FETCH_WORKERS)
        ]

        # Wait for all links to be fetched
        await fetch_queue.join()

        # Stop fetch workers
        for worker in fetch_workers:
            worker.cancel()
        await asyncio.gather(*fetch_workers, return_exceptions=True)


    # Wait for all classifications to complete
    await classification_queue.join()

    # Stop classification workers
    for _ in range(CLASSIFICATION_WORKERS):
        await classification_queue.put(None)
    await asyncio.gather(*classification_workers)

    # Add permanently failed items to results
    while not failed_classifications.empty():
        results.append(await failed_classifications.get())

    # Create index and classifications from results
    index = []
    classifications = {}
    for result in results:
        if "classification" in result:
            classifications[result["link"]] = result["classification"]
        # ensure we don't have content in the index
        result.pop("content", None)
        index.append(result)

    # Save index
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    # Save classifications
    with open(CLASSIFICATIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(classifications, f, indent=2, ensure_ascii=False)

    print(f"\nEnhanced crawling complete!")
    print(f"Processed {len(index)}/{total} links")
    print(f"Index saved to {INDEX_JSON}")
    print(f"Classifications saved to {CLASSIFICATIONS_JSON}")

def main():
    """Original main function for compatibility"""
    asyncio.run(main_enhanced())

if __name__ == "__main__":
    main()