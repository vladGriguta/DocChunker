"""
Text processing utilities for document chunking.
"""

from functools import lru_cache
import os
from pathlib import Path
import re

import tiktoken


def get_file_extension(file_path: str | Path) -> str:
    return os.path.splitext(file_path)[1].lower()[1:]


def normalize_whitespace(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n\n', text)
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

@lru_cache(maxsize=None)
def count_tokens_in_text(text: str) -> int:
    """
    Count the number of tokens in the text using tiktoken. Assuming the embedding model is 'cl100k_base' from openai.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    return len(tokens)
