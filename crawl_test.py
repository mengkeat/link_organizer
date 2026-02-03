import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode


async def main():
    config = CrawlerRunConfig(
        css_selector="main.content",
        word_count_threshold=10,
        excluded_tags=["nav", "footer"],
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_domains=["ads.com", "spammytrackers.net"],
        exclude_external_images=True,
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://news.ycombinator.com", config=config)
        print("Cleaned HTML length:", len(result.cleaned_html))


if __name__ == "__main__":
    asyncio.run(main())
