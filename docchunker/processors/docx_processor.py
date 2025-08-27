from typing import BinaryIO
from docchunker.models.chunk import Chunk
from docchunker.processors.base_processor import BaseProcessor
from docchunker.processors.document_chunker import DocumentChunker
from docchunker.processors.docx_parser import DocxParser


class DocxProcessor(BaseProcessor):
    """Main processor that orchestrates parsing and chunking"""
    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        super().__init__(chunk_size=chunk_size, num_overlapping_elements=num_overlapping_elements)
        self.parser = DocxParser()
        self.chunker = DocumentChunker(chunk_size, num_overlapping_elements=num_overlapping_elements)

    def process(self, file_input: str | BinaryIO) -> list[Chunk]:
        """Process DOCX file and return chunks.
        
        Args:
            file_input: Either a file path (str) or a file-like object (BinaryIO)
        """
        # Step 1: Parse to tagged elements
        elements = self.parser.apply(file_input)

        # Step 2: Convert to chunks
        # For file-like objects, use a generic identifier for chunker
        source_identifier = file_input if isinstance(file_input, str) else "<BytesIO>"
        chunks = self.chunker.apply(elements, source_identifier, source_format="docx")

        return chunks