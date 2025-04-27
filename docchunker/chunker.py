"""
Main chunker module for processing documents with complex structures.
"""

import os
from typing import Dict, List, Optional, Union
import json

from docchunker.models.chunk import Chunk
from docchunker.models.document import Document
from docchunker.processors.docx_processor import DocxProcessor
from docchunker.processors.pdf_processor import PdfProcessor
from docchunker.utils.text_utils import get_file_extension


class DocChunker:
    """
    Main class for chunking documents with complex structures.
    
    This class handles the high-level chunking logic, delegating specific
    format processing to specialized processors.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        preserve_structure: bool = True,
        handle_tables: bool = True,
        handle_lists: bool = True,
        handle_images: bool = False,
    ):
        """
        Initialize the DocChunker with specific settings.
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            preserve_structure: Whether to preserve document structure when chunking
            handle_tables: Whether to specially process tables
            handle_lists: Whether to specially process lists
            handle_images: Whether to extract and process images
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_structure = preserve_structure
        self.handle_tables = handle_tables
        self.handle_lists = handle_lists
        self.handle_images = handle_images
        
        # Initialize processors
        self.processors = {
            "docx": DocxProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_structure=preserve_structure,
                handle_tables=handle_tables,
                handle_lists=handle_lists,
                handle_images=handle_images,
            ),
            "pdf": PdfProcessor(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_structure=preserve_structure,
                handle_tables=handle_tables,
                handle_lists=handle_lists,
                handle_images=handle_images,
            ),
        }
    
    def process_document(self, file_path: str) -> List[Chunk]:
        """
        Process a document and return a list of chunks.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of Chunk objects
            
        Raises:
            ValueError: If the file format is not supported
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = get_file_extension(file_path)
        
        if extension not in self.processors:
            raise ValueError(f"Unsupported file format: {extension}")
        
        processor = self.processors[extension]
        document = processor.process(file_path)
        chunks = processor.chunk(document)
        
        return chunks
    
    def process_documents(self, directory_path: str, recursive: bool = False) -> Dict[str, List[Chunk]]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory_path: Path to the directory containing documents
            recursive: Whether to process documents in subdirectories
            
        Returns:
            Dictionary mapping file paths to lists of chunks
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        results = {}
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                extension = get_file_extension(file_path)
                
                if extension in self.processors:
                    try:
                        chunks = self.process_document(file_path)
                        results[file_path] = chunks
                    except Exception as e:
                        print(f"Error processing {file_path}: {str(e)}")
            
            if not recursive:
                break
        
        return results
    
    def export_chunks_to_json(self, chunks: List[Chunk], output_file: str) -> None:
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