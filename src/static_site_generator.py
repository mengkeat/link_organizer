"""
Static site generator for link collection
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SiteConfig:
    """Configuration for static site generation"""
    title: str = "My Link Collection"
    description: str = "Organized collection of saved links"
    output_dir: str = "public"
    theme: str = "default"


class StaticSiteGenerator:
    """Generates static HTML site from link collection"""
    
    def __init__(self, config: Optional[SiteConfig] = None):
        self.config = config or SiteConfig()
        
    def generate(self, index_file: Path, classifications_file: Optional[Path] = None) -> Path:
        """Generate static site from index and classifications."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Load data
        index_data = json.loads(index_file.read_text()) if index_file.exists() else []
        classifications = {}
        if classifications_file and classifications_file.exists():
            classifications = json.loads(classifications_file.read_text())
        
        # Merge classification data into index
        for item in index_data:
            link = item.get('link', '')
            if link in classifications:
                item['classification'] = classifications[link]
        
        # Group by category
        categories = self._group_by_category(index_data)
        
        # Generate pages
        self._generate_index_page(output_dir, categories, index_data)
        self._generate_category_pages(output_dir, categories)
        self._generate_css(output_dir)
        
        print(f"Static site generated at {output_dir.absolute()}")
        return output_dir
    
    def _group_by_category(self, index_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Group links by their classification category."""
        categories = {}
        for item in index_data:
            category = "Uncategorized"
            if 'classification' in item and item['classification']:
                category = item['classification'].get('category', 'Uncategorized')
            
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        return categories
    
    @staticmethod
    def _safe_category_slug(category: str) -> str:
        """Convert category name to a filesystem-safe slug."""
        import re
        slug = category.replace(' ', '-').replace('/', '-').lower()
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        return slug or 'uncategorized'

    def _generate_index_page(self, output_dir: Path, categories: Dict, all_links: List[Dict]):
        """Generate main index.html page."""
        total_links = len(all_links)
        success_count = sum(1 for item in all_links if item.get('status') == 'Success')
        
        categories_html = ""
        for category, links in sorted(categories.items()):
            safe_category = self._safe_category_slug(category)
            categories_html += f'''
            <div class="category-card">
                <h3><a href="category-{safe_category}.html">{category}</a></h3>
                <p>{len(links)} links</p>
            </div>
            '''
        
        # Recent links (last 20)
        recent_links = sorted(
            [l for l in all_links if l.get('status') == 'Success'],
            key=lambda x: x.get('id', ''),
            reverse=True
        )[:20]
        
        recent_html = self._render_link_list(recent_links)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>{self.config.title}</h1>
        <p>{self.config.description}</p>
        <div class="stats">
            <span>Total: {total_links} links</span>
            <span>Saved: {success_count} links</span>
            <span>Categories: {len(categories)}</span>
        </div>
    </header>
    
    <main>
        <section class="categories">
            <h2>Categories</h2>
            <div class="category-grid">
                {categories_html}
            </div>
        </section>
        
        <section class="recent">
            <h2>Recent Links</h2>
            <div class="link-list">
                {recent_html}
            </div>
        </section>
    </main>
    
    <footer>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </footer>
</body>
</html>'''
        
        (output_dir / "index.html").write_text(html, encoding='utf-8')
    
    def _generate_category_pages(self, output_dir: Path, categories: Dict):
        """Generate individual category pages."""
        for category, links in categories.items():
            safe_category = self._safe_category_slug(category)
            links_html = self._render_link_list(links)
            
            html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} - {self.config.title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <a href="index.html" class="back-link">← Back to Home</a>
        <h1>{category}</h1>
        <p>{len(links)} links in this category</p>
    </header>
    
    <main>
        <div class="link-list">
            {links_html}
        </div>
    </main>
    
    <footer>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </footer>
</body>
</html>'''
            
            (output_dir / f"category-{safe_category}.html").write_text(html, encoding='utf-8')
    
    def _render_link_list(self, links: List[Dict]) -> str:
        """Render a list of links as HTML."""
        html = ""
        for item in links:
            link = item.get('link', '')
            status = item.get('status', 'Unknown')
            classification = item.get('classification', {})
            
            summary = classification.get('summary', '') if classification else ''
            tags = classification.get('tags', []) if classification else []
            difficulty = classification.get('difficulty', '') if classification else ''
            
            tags_html = ''.join(f'<span class="tag">{tag}</span>' for tag in tags[:5])
            status_class = 'success' if status == 'Success' else 'failed'
            
            html += f'''
            <div class="link-item {status_class}">
                <a href="{link}" target="_blank" class="link-url">{link[:80]}{'...' if len(link) > 80 else ''}</a>
                {f'<p class="summary">{summary}</p>' if summary else ''}
                <div class="meta">
                    <div class="tags">{tags_html}</div>
                    {f'<span class="difficulty">{difficulty}</span>' if difficulty else ''}
                </div>
            </div>
            '''
        return html
    
    def _generate_css(self, output_dir: Path):
        """Generate CSS stylesheet."""
        css = '''
:root {
    --bg-color: #1a1a2e;
    --card-bg: #16213e;
    --text-color: #eee;
    --text-muted: #888;
    --accent: #00d9ff;
    --success: #4ade80;
    --error: #f87171;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    padding: 2rem;
}

header {
    text-align: center;
    margin-bottom: 3rem;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    color: var(--accent);
}

.stats {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1rem;
    color: var(--text-muted);
}

.back-link {
    display: inline-block;
    margin-bottom: 1rem;
    color: var(--accent);
    text-decoration: none;
}

main {
    max-width: 1200px;
    margin: 0 auto;
}

section {
    margin-bottom: 3rem;
}

h2 {
    margin-bottom: 1.5rem;
    color: var(--accent);
}

.category-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
}

.category-card {
    background: var(--card-bg);
    padding: 1.5rem;
    border-radius: 8px;
    transition: transform 0.2s;
}

.category-card:hover {
    transform: translateY(-2px);
}

.category-card a {
    color: var(--text-color);
    text-decoration: none;
}

.category-card p {
    color: var(--text-muted);
    font-size: 0.9rem;
}

.link-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.link-item {
    background: var(--card-bg);
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 3px solid var(--accent);
}

.link-item.failed {
    border-left-color: var(--error);
    opacity: 0.7;
}

.link-url {
    color: var(--accent);
    text-decoration: none;
    word-break: break-all;
    font-weight: 500;
}

.link-url:hover {
    text-decoration: underline;
}

.summary {
    margin-top: 0.5rem;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 0.75rem;
    flex-wrap: wrap;
}

.tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.tag {
    background: rgba(0, 217, 255, 0.1);
    color: var(--accent);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
}

.difficulty {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: capitalize;
}

footer {
    text-align: center;
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid var(--card-bg);
    color: var(--text-muted);
}

@media (max-width: 600px) {
    body {
        padding: 1rem;
    }
    
    .stats {
        flex-direction: column;
        gap: 0.5rem;
    }
}
'''
        (output_dir / "styles.css").write_text(css, encoding='utf-8')
