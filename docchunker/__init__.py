"""
DocChunker: A specialized document chunking library for complex document structures.

This library provides tools to process and chunk documents with complex structures
including tables, nested lists, and images in formats like DOCX and PDF.
"""

from docchunker.chunker import DocChunker
from docchunker.models.chunk import Chunk

__version__ = "0.1.4"
__all__ = ["DocChunker", "Chunk"]