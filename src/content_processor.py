"""
Content processing utilities for extracting and handling different file types
"""
import hashlib
from pathlib import Path
from typing import Optional
import PyPDF2


class ContentProcessor:
    """Handles content extraction from various file formats"""

    @staticmethod
    def extract_content_from_file(file_path: Path) -> str:
        """Extract text content from markdown or PDF files"""
        try:
            if file_path.suffix.lower() == '.md':
                return file_path.read_text(encoding='utf-8')
            elif file_path.suffix.lower() == '.pdf':
                return ContentProcessor.extract_pdf_text(file_path)
            else:
                return f"Unsupported file type: {file_path.suffix}"
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    @staticmethod
    def extract_pdf_text(file_path: Path) -> str:
        """Extract text from PDF files"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            return f"Error extracting PDF text: {e}"

    @staticmethod
    def hash_link(link: str) -> str:
        """Generate hash for link (matching existing system)"""
        return hashlib.sha256(link.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_title_from_url(url: str) -> str:
        """Generate a readable title from URL"""
        return url.split('/')[-1].replace('-', ' ').replace('_', ' ').title()