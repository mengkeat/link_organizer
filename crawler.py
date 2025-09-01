#!/usr/bin/env python3
"""
Unified Link Crawler with Optional Classification
A simplified, single-file crawler that processes links with optional AI classification
"""

import os
import hashlib
import asyncio
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

import requests
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from get_count_links import extract_links_from_file
from src.database import db
from src.models import LinkData, ClassificationResult


class LinkCrawler:
    """Simplified link crawler with optional classification"""
    
    def __init__(self, classify=False, max_concurrent=5):
        self.classify = classify
        self.max_concurrent = max_concurrent
        self.data_dir = "dat"
        self.classification_service = None
        
        if classify:
            from src.classification import ClassificationService
            self.classification_service = ClassificationService()
    
    @staticmethod
    def hash_link(link):
        """Generate SHA256 hash for a URL string."""
        return hashlib.sha256(link.encode("utf-8")).hexdigest()
    
    @staticmethod
    def is_pdf(url):
        """Check if URL points to a PDF file."""
        return url.lower().endswith(".pdf") or "pdf" in urlparse(url).path.lower()
    
    @staticmethod
    def generate_title_from_url(url):
        """Generate a simple title from URL."""
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1]
        if path and path != parsed.netloc:
            return path.replace('-', ' ').replace('_', ' ').title()
        return parsed.netloc.replace('www.', '').title()
    
    async def fetch_content(self, crawler, url):
        """Fetch content from URL (PDF or HTML)."""
        if self.is_pdf(url):
            # Download PDF directly
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.content, "pdf"
        
        # Use crawl4ai for HTML/Markdown
        config = CrawlerRunConfig(
            word_count_threshold=10,
            excluded_tags=["nav", "footer"],
            exclude_external_links=True,
            exclude_social_media_links=True,
            exclude_external_images=True,
            cache_mode=CacheMode.BYPASS,
        )
        
        result = await crawler.arun(url=url, config=config)
        if result.success:
            return result.markdown, "md"
        else:
            raise Exception(f"Failed to crawl: {result.error_message}")
    
    async def process_link(self, crawler, link, idx, total):
        """Process a single link: fetch, save, and optionally classify."""
        link_id = self.hash_link(link)
        print(f"[{idx+1}/{total}] Processing: {link}")
        
        # Check if already processed
        existing = db.get_link_by_url(link)
        if existing:
            print(f"[{idx+1}/{total}] Already exists: {link}")
            return existing
        
        try:
            # Fetch content
            content, file_type = await self.fetch_content(crawler, link)
            
            # Save to file
            filename = f"{link_id}.{file_type}"
            filepath = os.path.join(self.data_dir, filename)
            mode = "wb" if file_type == "pdf" else "w"
            encoding = None if file_type == "pdf" else "utf-8"
            
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)
            
            # Create LinkData
            link_data = LinkData(
                link=link,
                id=link_id,
                filename=filename,
                status="Success",
                content=content if file_type != 'pdf' else None
            )
            
            # Optional classification
            if self.classify and self.classification_service and content and file_type != 'pdf':
                try:
                    title = self.generate_title_from_url(link)
                    classification = await self.classification_service.classify_content(
                        link, title, content
                    )
                    link_data.classification = classification
                    print(f"[{idx+1}/{total}] Classified: {classification.category}")
                except Exception as e:
                    print(f"[{idx+1}/{total}] Classification failed: {e}")
            
            # Save to database
            db.save_link_data(link_data)
            print(f"[{idx+1}/{total}] Success: {link} -> {filename}")
            return link_data
            
        except Exception as e:
            print(f"[{idx+1}/{total}] Failed: {link}: {e}")
            link_data = LinkData(
                link=link,
                id=link_id,
                filename=None,
                status=f"Failed: {e}"
            )
            db.save_link_data(link_data)
            return link_data
    
    async def crawl_links(self, links):
        """Crawl all links with controlled concurrency."""
        os.makedirs(self.data_dir, exist_ok=True)
        total = len(links)
        results = []
        
        print(f"Starting to process {total} links...")
        if self.classify:
            print("Classification enabled")
        
        async with AsyncWebCrawler() as crawler:
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_with_semaphore(idx, link):
                async with semaphore:
                    return await self.process_link(crawler, link, idx, total)
            
            tasks = [process_with_semaphore(idx, link) for idx, link in enumerate(links)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and get successful results
        successful = [r for r in results if isinstance(r, LinkData) and r.status == "Success"]
        failed = [r for r in results if isinstance(r, LinkData) and "Failed" in r.status]
        
        print(f"\nProcessing complete!")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        # Save summary files
        self.save_summary(results)
        
        return results
    
    def save_summary(self, results):
        """Save processing summary to JSON files."""
        # Create index file
        index_data = []
        classifications = {}
        
        for result in results:
            if isinstance(result, LinkData):
                index_data.append(result.to_dict())
                if result.classification:
                    classifications[result.link] = {
                        'category': result.classification.category,
                        'subcategory': result.classification.subcategory,
                        'tags': result.classification.tags,
                        'summary': result.classification.summary,
                        'confidence': result.classification.confidence
                    }
        
        # Save index
        with open("index.json", "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)
        print(f"Index saved to index.json")
        
        # Save classifications if any
        if classifications:
            with open("classifications.json", "w", encoding="utf-8") as f:
                json.dump(classifications, f, indent=2)
            print(f"Classifications saved to classifications.json")


def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description="Unified Link Crawler")
    parser.add_argument("--classify", action="store_true", 
                       help="Enable AI classification of content")
    parser.add_argument("--workers", type=int, default=5,
                       help="Number of concurrent workers (default: 5)")
    parser.add_argument("--input", default="links.md",
                       help="Input file with links (default: links.md)")
    
    args = parser.parse_args()
    
    # Load environment variables for classification
    if args.classify:
        load_dotenv()
    
    # Extract links
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return
    
    links = extract_links_from_file(args.input)
    if not links:
        print(f"No links found in {args.input}")
        return
    
    # Create crawler and process links
    crawler = LinkCrawler(classify=args.classify, max_concurrent=args.workers)
    asyncio.run(crawler.crawl_links(links))


if __name__ == "__main__":
    main()