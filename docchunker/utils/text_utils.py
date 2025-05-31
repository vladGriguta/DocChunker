"""
Text processing utilities for document chunking.
"""

import os
import re


def get_file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()[1:]


def normalize_whitespace(text: str) -> str:
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Replace multiple newlines with double newline
    text = re.sub(r'\n+', '\n\n', text)
    # Trim whitespace at start and end
    return text.strip()


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    Extract top keywords from text.
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to extract
    Returns:
        List of keywords
    """
    raise NotImplementedError("Keyword extraction is not implemented yet.")