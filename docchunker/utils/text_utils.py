"""
Text processing utilities for document chunking.
"""

import os
import re
from typing import List, Optional, Union


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension without the dot, e.g., "pdf", "docx"
    """
    return os.path.splitext(file_path)[1].lower()[1:]


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Replace multiple newlines with double newline
    text = re.sub(r'\n+', '\n\n', text)
    # Trim whitespace at start and end
    return text.strip()


def detect_language(text: str) -> str:
    """
    Attempt to detect the language of text.
    
    Args:
        text: Input text
        
    Returns:
        ISO 639-1 language code (e.g., "en", "fr")
    """
    # This is a very simplistic implementation
    # In a real system, you'd use a library like langdetect or pycld2
    
    # Default to English
    return "en"


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Estimate reading time in minutes.
    
    Args:
        text: Input text
        words_per_minute: Reading speed in words per minute
        
    Returns:
        Estimated reading time in minutes
    """
    word_count = len(text.split())
    return max(1, round(word_count / words_per_minute))


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract top keywords from text.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of keywords
    """
    # This is a simplistic implementation
    # In a real system, you'd use a library like NLTK, spaCy, or an ML model
    
    # Convert to lowercase and split into words
    words = text.lower().split()
    
    # Remove common punctuation and strip whitespace
    words = [word.strip('.,;:!?()[]{}""\'').strip() for word in words]
    
    # Remove empty strings and words with less than 3 characters
    words = [word for word in words if word and len(word) >= 3]