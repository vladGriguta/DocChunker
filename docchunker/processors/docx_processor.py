from typing import BinaryIO
from docchunker.models.chunk import Chunk
from docchunker.processors.base_processor import BaseProcessor
from docchunker.processors.docx_chunker import DocxChunker
from docchunker.processors.docx_parser import DocxParser
from docchunker.utils.io_utils import write_json


class DocxProcessor(BaseProcessor):
    """Main processor that orchestrates parsing and chunking"""
    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        super().__init__(chunk_size=chunk_size, num_overlapping_elements=num_overlapping_elements)
        self.parser = DocxParser()
        self.chunker = DocxChunker(chunk_size, num_overlapping_elements=num_overlapping_elements)

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
        chunks = self.chunker.apply(elements, source_identifier)

        return chunks