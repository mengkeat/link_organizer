"""
Crawler utilities for fetching and processing web content
"""
import os
import base64
import requests
from urllib.parse import urlparse
from crawl4ai import CrawlerRunConfig, CacheMode
from typing import Tuple, Optional
from PIL import Image
from io import BytesIO

from .models import LinkData
from .content_processor import ContentProcessor


class CrawlerUtils:
    """Utilities for web crawling operations"""

    @staticmethod
    def is_pdf(url: str) -> bool:
        """Check if URL points to a PDF file based on extension or path."""
        return url.lower().endswith(".pdf") or "pdf" in urlparse(url).path.lower()

    @staticmethod
    async def fetch_and_convert(crawler, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Fetch content from URL and convert to appropriate format (PDF or markdown)."""
        if CrawlerUtils.is_pdf(url):
            content, typ = CrawlerUtils._download_pdf(url)
            return content, typ, None
        else:
            return await CrawlerUtils._fetch_html_content(crawler, url)

    @staticmethod
    def _download_pdf(url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download PDF content directly from URL."""
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.content, "pdf"
        except Exception as e:
            print(f"Failed to download PDF from {url}: {e}")
            return None, None

    @staticmethod
    async def _fetch_html_content(crawler, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch HTML content and convert to markdown using crawler.
        Reference for options can be found here: https://docs.crawl4ai.com/api/parameters/#2-crawlerrunconfig-controlling-each-crawl
        """
        config = CrawlerRunConfig(
            css_selector=None,
            word_count_threshold=10,
            excluded_tags=["nav", "footer"],
            exclude_external_links=True,
            exclude_social_media_links=True,
            exclude_domains=[],
            exclude_external_images=True,
            cache_mode=CacheMode.BYPASS,
            magic=True, # auto handling of popups and content banners
            screenshot=True, 
        )
        
        try:
            result = await crawler.arun(url=url, config=config)
            if result.success:
                screenshot_base64 = result.screenshot if hasattr(result, 'screenshot') and result.screenshot else None
                return result.markdown, "md", screenshot_base64
            else:
                print(f"Crawling failed for {url}")
                return None, None, None
        except Exception as e:
            print(f"Error fetching HTML content from {url}: {e}")
            return None, None, None

    @staticmethod
    def _save_screenshot(screenshot_base64: str, link_id: str, data_dir: str) -> Optional[str]:
        """Save base64 screenshot as JPEG file."""
        try:
            screenshot_data = base64.b64decode(screenshot_base64)
            image = Image.open(BytesIO(screenshot_data))
            
            # Convert to RGB if necessary (in case it's RGBA)
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            
            screenshot_filename = f"{link_id}_screenshot.jpg"
            screenshot_path = os.path.join(data_dir, screenshot_filename)
            
            image.save(screenshot_path, 'JPEG', quality=85)
            return screenshot_filename
            
        except Exception as e:
            print(f"Failed to save screenshot: {e}")
            return None

    @staticmethod
    async def fetch_link_content(crawler, link: str, idx: int, total: int, data_dir: str = "dat") -> LinkData:
        """Fetch content for a link and prepare LinkData object with status."""
        link_id = ContentProcessor.hash_link(link)
        print(f"[{idx+1}/{total}] Fetching: {link}")
        
        try:
            content, typ, screenshot_base64 = await CrawlerUtils.fetch_and_convert(crawler, link)
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

            # Save screenshot if available
            screenshot_filename = None
            if screenshot_base64:
                screenshot_filename = CrawlerUtils._save_screenshot(screenshot_base64, link_id, data_dir)

            content_str = content if typ != "pdf" else f"PDF content ({len(content)} bytes)"
            return LinkData(
                link=link,
                id=link_id,
                filename=filename,
                content=content_str,
                screenshot_filename=screenshot_filename,
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