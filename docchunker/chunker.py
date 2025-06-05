import os
import json
from pathlib import Path

from docchunker.models.chunk import Chunk
from docchunker.processors.docx_processor import DocxProcessor
from docchunker.processors.pdf_processor import PdfProcessor
from docchunker.utils.text_utils import get_file_extension


class DocChunker:
    """
    Main class for chunking documents with complex structures.
    
    This class handles the high-level chunking logic, delegating specific
    format processing to specialized processors.
    """

    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements

        self.processors = {
            "docx": DocxProcessor(chunk_size=chunk_size, num_overlapping_elements=num_overlapping_elements),
            "pdf": PdfProcessor(chunk_size=chunk_size, num_overlapping_elements=num_overlapping_elements),
        }

    def process_document(self, file_path: str | Path) -> list[Chunk]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = get_file_extension(file_path)

        if extension not in self.processors:
            raise ValueError(f"Unsupported file format: {extension}")

        processor = self.processors[extension]
        chunks = processor.process(file_path)
        return chunks

    def process_documents(self, dir_path: str, regex_pattern: str) -> list[Chunk]:
        all_chunks = []
        for file_path in Path(dir_path).rglob(regex_pattern):
            chunks = self.process_document(str(file_path))
            all_chunks.extend(chunks)
        return all_chunks

    def export_chunks_to_json(self, chunks: list[Chunk], output_file: str | Path) -> None:
        """
        Export chunks to a JSON file.
        Args:
            chunks: List of chunks to export
            output_file: Path to the output file
        """
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [{"text": c.text, "metadata": c.metadata} for c in chunks],
                f,
                indent=2
            )