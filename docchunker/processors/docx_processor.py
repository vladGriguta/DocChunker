from docchunker.models.chunk import Chunk
from docchunker.processors.docx_chunker import TaggedChunker
from docchunker.processors.docx_parser import DocxParser
from docchunker.utils.io_utils import write_json


class DocxProcessor:
    """Main processor that orchestrates parsing and chunking"""
    
    def __init__(self, chunk_size: int = 1000):
        self.parser = DocxParser()
        self.chunker = TaggedChunker(chunk_size)
    
    def process(self, file_path: str) -> list[Chunk]:
        """Process DOCX file and return chunks"""
        # Step 1: Parse to tagged elements
        elements = self.parser.parse(file_path)
        write_json('parsed_elements.json', elements)
        
        # Step 2: Convert to chunks
        chunks = self.chunker.chunk(elements, file_path)
        
        return chunks