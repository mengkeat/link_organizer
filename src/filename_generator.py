"""
Filename generation utilities for creating readable filenames from URLs
"""
import re
from urllib.parse import urlparse, unquote
from typing import Optional
from datetime import datetime


class FilenameGenerator:
    """Generates human-readable filenames from URLs"""
    
    @staticmethod
    def generate_readable_filename(url: str, content_type: str = "md", max_length: int = 80) -> str:
        """
        Generate a human-readable filename from URL.
        
        Examples:
            https://arxiv.org/abs/2105.00613 -> arxiv-2105-00613.md
            https://github.com/user/repo -> github-user-repo.md
            https://example.com/blog/my-post -> example-blog-my-post.md
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').split('.')[0]  # Get main domain name
        
        # Get path parts, clean them
        path = unquote(parsed.path).strip('/')
        path_parts = [p for p in path.split('/') if p and p not in ['pdf', 'html', 'htm']]
        
        # Build filename from domain + path parts
        parts = [domain] + path_parts[-3:]  # Limit to last 3 path segments
        
        # Clean each part
        cleaned_parts = []
        for part in parts:
            # Remove file extensions
            part = re.sub(r'\.(pdf|html?|md|txt)$', '', part, flags=re.IGNORECASE)
            # Replace special chars with hyphens
            part = re.sub(r'[^\w\-]', '-', part)
            # Collapse multiple hyphens
            part = re.sub(r'-+', '-', part)
            # Remove leading/trailing hyphens
            part = part.strip('-')
            if part:
                cleaned_parts.append(part.lower())
        
        # Join and truncate
        filename = '-'.join(cleaned_parts)
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit('-', 1)[0]
        
        # Ensure filename is not empty
        if not filename:
            filename = f"link-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return f"{filename}.{content_type}"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove or replace characters that are invalid in filenames."""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        return filename
    
    @staticmethod
    def make_unique_filename(filename: str, existing_filenames: set) -> str:
        """
        Ensure filename is unique by appending a counter if needed.
        """
        if filename not in existing_filenames:
            return filename
        
        base, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        counter = 1
        while True:
            new_filename = f"{base}-{counter}.{ext}" if ext else f"{base}-{counter}"
            if new_filename not in existing_filenames:
                return new_filename
            counter += 1
