import os
import re
import hashlib
import json
import asyncio
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from get_count_links import extract_links_from_file

LINKS_MD = "links.md"
DATA_DIR = "dat"
INDEX_JSON = "index.json"

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
        cache_mode=CacheMode.BYPASS
    )
    result = await crawler.arun(url=url, config=config)
    if result.success:
        return result.markdown, "md"
    else:
        return "", None

async def main_async():
    os.makedirs(DATA_DIR, exist_ok=True)
    links = extract_links_from_file(LINKS_MD)
    print(f"Found {len(links)} links in {LINKS_MD}")
    index = []
    async with AsyncWebCrawler() as crawler:
        for link in links:
            id_ = hash_link(link)
            print(f"Processing: {link} with hash {id_}")
            try:
                content, typ = await fetch_and_convert(crawler, link)
                fname = f"{id_}.{typ}"
                fpath = os.path.join(DATA_DIR, fname)
                mode = "wb" if typ == "pdf" else "w"
                with open(fpath, mode, encoding=None if typ == "pdf" else "utf-8") as f:
                    f.write(content)
                index.append({"link": link, "id": id_, "filename": fname, "status": "Success"})
                print(f"Success: {link} -> {fname}")
            except Exception as e:
                index.append({"link": link, "id": id_, "filename": None, "status": f"Failed: {e}"})
                print(f"Failed: {link}: {e}")
    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
