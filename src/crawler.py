"""
Crawler and content processing logic.
"""
import os
import json
import asyncio
import base64
import requests
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Set, Any
from urllib.parse import urlparse, unquote
from PIL import Image
from io import BytesIO
import PyPDF2
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

from .core import get_logger, LinkData, ProcessingStage, CrawlerConfig, get_config
from .index import IndexEntry, LinkIndex
from .classifier import ClassificationService
from .memory import MemoryRouter, MemoryLinkEntry, MarkdownWriter, LinkMarkdownWriter, TopicIndexManager, LiteLLMEmbeddingClient

logger = get_logger("crawler")

# --- Content Processing & Filenames ---

class ContentProcessor:
    @staticmethod
    def extract_content_from_file(file_path: Path) -> str:
        try:
            if file_path.suffix.lower() == '.md': return file_path.read_text(encoding='utf-8')
            if file_path.suffix.lower() == '.pdf': return ContentProcessor.extract_pdf_text(file_path)
            return f"Unsupported file type: {file_path.suffix}"
        except Exception as e: return f"Error reading file {file_path}: {e}"

    @staticmethod
    def extract_pdf_text(file_path: Path) -> str:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f); text = ""
                for page in reader.pages: text += page.extract_text() + "\n"
                return text
        except Exception as e: return f"Error extracting PDF text: {e}"

    @staticmethod
    def hash_link(link: str) -> str: return hashlib.sha256(link.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_title_from_url(url: str) -> str:
        if url.endswith('/'): return ""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path: return parsed.netloc.replace('www.', '').title()
        return path.split('/')[-1].replace('-', ' ').replace('_', ' ').title()

class FilenameGenerator:
    @staticmethod
    def generate_readable_filename(url: str, ext: str = "md") -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').split('.')[0]
        path = unquote(parsed.path).strip('/')
        parts = [domain] + [p for p in path.split('/') if p and p not in ['pdf', 'html', 'md']][-3:]
        cleaned = [re.sub(r'[^\w\-]', '-', p).strip('-').lower() for p in parts if p]
        return f"{'-'.join(cleaned) or 'link'}.{ext}"

# --- Crawler ---

class UnifiedCrawler:
    def __init__(self, workers: int = 5, incremental: bool = True):
        self.workers = workers
        self.incremental = incremental
        self.config = get_config()
        self._classifier = ClassificationService()
        self._index = LinkIndex(Path(self.config.crawler.index_file))
        self._setup_memory()

    def _setup_memory(self):
        conf = self.config.memory
        self.memory_router = MemoryRouter(
            LiteLLMEmbeddingClient(model=conf.embedding_model),
            TopicIndexManager(Path(conf.topic_index_db)),
            MarkdownWriter(Path(conf.output_dir) / conf.topics_subdir),
            similarity_threshold=conf.similarity_threshold
        )
        self.link_writer = LinkMarkdownWriter(Path(conf.output_dir) / conf.links_subdir)

    async def run(self, links: List[str]):
        os.makedirs(self.config.crawler.data_dir, exist_ok=True)
        if self.incremental:
            successful = self._index.get_successful_links()
            links = [l for l in links if l not in successful]
        
        if not links:
            logger.info("No new links to process.")
            return

        queue = asyncio.Queue()
        for i, link in enumerate(links): await queue.put((i, link))
        
        async with AsyncWebCrawler() as crawler:
            tasks = [self._worker(crawler, queue, len(links)) for _ in range(self.workers)]
            await asyncio.gather(*tasks)
        
        self._index.save()
        logger.info("Sync complete.")

    async def _worker(self, crawler, queue, total):
        while not queue.empty():
            idx, link = await queue.get()
            try:
                logger.info("[%d/%d] Processing: %s", idx + 1, total, link)
                content, ext, screenshot = await self._fetch(crawler, link)
                if not content: raise ValueError("No content fetched")
                
                fname = FilenameGenerator.generate_readable_filename(link, ext)
                fpath = Path(self.config.crawler.data_dir) / fname
                fpath.write_bytes(content) if ext == "pdf" else fpath.write_text(content, encoding="utf-8")
                
                # Classify
                title = ContentProcessor.generate_title_from_url(link)
                content_sample = content if ext != "pdf" else "PDF content"
                classification = await self._classifier.classify_content(link, title, content_sample)
                
                # Route to memory
                mem_entry = MemoryLinkEntry(
                    url=link, title=title, tags=classification.tags,
                    summary=classification.summary, key_topics=classification.key_topics,
                    content_markdown=content if ext == "md" else "",
                    content_type=ext
                )
                topic_id = await self.memory_router.route_link(mem_entry, content if ext == "md" else "", classification.category)
                topic_file = self.memory_router.index_manager.get_topic(topic_id).filename
                note_path = self.link_writer.write_link_note(mem_entry, topic_id, topic_file)

                # Update index
                entry = IndexEntry(
                    link=link, id=ContentProcessor.hash_link(link),
                    filename=fname, readable_filename=fname, status="Success",
                    crawled_at=datetime.now().isoformat(),
                    classification=classification.model_dump(),
                    memory_topic_id=topic_id, memory_topic_file=topic_file,
                    memory_link_file=note_path
                )
                self._index.add(entry)
                logger.info("[%d/%d] Success: %s", idx + 1, total, link)
                
            except Exception as e:
                logger.error("[%d/%d] Failed: %s - %s", idx + 1, total, link, e)
                self._index.add(IndexEntry(link=link, id=ContentProcessor.hash_link(link), status=f"Failed: {e}"))
            finally:
                queue.task_done()

    async def _fetch(self, crawler, url: str) -> Tuple[Optional[Any], str, Optional[str]]:
        if url.lower().endswith(".pdf") or "pdf" in urlparse(url).path.lower():
            resp = requests.get(url, timeout=15)
            return resp.content, "pdf", None
        
        conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, magic=True, screenshot=True)
        result = await crawler.arun(url=url, config=conf)
        if result.success:
            return result.markdown, "md", result.screenshot
        return None, "md", None
