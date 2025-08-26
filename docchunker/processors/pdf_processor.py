"""
Processor for PDF documents.
"""

from typing import BinaryIO
from docchunker.models.chunk import Chunk


from docchunker.processors.base_processor import BaseProcessor

class PdfProcessor(BaseProcessor):
    """
    Processor for PDF documents.
    
    This class handles the extraction and chunking of content from PDF files,
    with special handling for complex structures like tables and lists.
    """

    def __init__(self, chunk_size: int = 1000, num_overlapping_elements: int = 0):
        super().__init__(chunk_size=chunk_size, num_overlapping_elements=num_overlapping_elements)

    def process(self, file_input: str | BinaryIO) -> list[Chunk]:
        """Process PDF file and return chunks"""
        raise NotImplementedError("PDF processing is not yet implemented.")
