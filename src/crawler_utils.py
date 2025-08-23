"""
Crawler utilities for fetching and processing web content
"""
import os
import requests
from urllib.parse import urlparse
from pathlib import Path
from crawl4ai import CrawlerRunConfig, CacheMode
from typing import Tuple, Optional

from .models import LinkData
from .content_processor import ContentProcessor


class CrawlerUtils:
    """Utilities for web crawling operations"""

    @staticmethod
    def is_pdf(url: str) -> bool:
        """Check if URL points to a PDF file"""
        return url.lower().endswith(".pdf") or "pdf" in urlparse(url).path.lower()

    @staticmethod
    async def fetch_and_convert(crawler, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch content from URL and convert to appropriate format"""
        if CrawlerUtils.is_pdf(url):
            return CrawlerUtils._download_pdf(url)
        else:
            return await CrawlerUtils._fetch_html_content(crawler, url)

    @staticmethod
    def _download_pdf(url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download PDF directly"""
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.content, "pdf"
        except Exception as e:
            print(f"Failed to download PDF from {url}: {e}")
            return None, None

    @staticmethod
    async def _fetch_html_content(crawler, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch HTML content and convert to markdown"""
        config = CrawlerRunConfig(
            css_selector=None,
            word_count_threshold=10,
            excluded_tags=["nav", "footer"],
            exclude_external_links=True,
            exclude_social_media_links=True,
            exclude_domains=[],
            exclude_external_images=True,
            cache_mode=CacheMode.BYPASS,
        )
        
        try:
            result = await crawler.arun(url=url, config=config)
            if result.success:
                return result.markdown, "md"
            else:
                print(f"Crawling failed for {url}")
                return None, None
        except Exception as e:
            print(f"Error fetching HTML content from {url}: {e}")
            return None, None

    @staticmethod
    async def fetch_link_content(crawler, link: str, idx: int, total: int, data_dir: str = "dat") -> LinkData:
        """Fetch content for a link and prepare LinkData object"""
        link_id = ContentProcessor.hash_link(link)
        print(f"[{idx+1}/{total}] Fetching: {link}")
        
        try:
            content, typ = await CrawlerUtils.fetch_and_convert(crawler, link)
            if not content:
                return LinkData(
                    link=link, 
                    id=link_id, 
                    filename=None, 
                    status="Failed: No content"
                )

            filename = f"{link_id}.{typ}"
            filepath = os.path.join(data_dir, filename)
            mode = "wb" if typ == "pdf" else "w"
            encoding = None if typ == "pdf" else "utf-8"
            
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)

            content_str = content if typ != "pdf" else f"PDF content ({len(content)} bytes)"
            return LinkData(
                link=link,
                id=link_id,
                filename=filename,
                content=content_str,
                status="Fetched"
            )
            
        except Exception as e:
            print(f"[{idx+1}/{total}] Failed to fetch {link}: {e}")
            return LinkData(
                link=link,
                id=link_id,
                filename=None,
                status=f"Failed: {e}"
            )