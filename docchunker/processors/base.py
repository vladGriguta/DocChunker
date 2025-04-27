"""
Base processor class for document processing.
"""

import os
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from docchunker.models.chunk import Chunk
from docchunker.models.document import Document


class BaseProcessor(ABC):
    """
    Abstract base class for document processors.
    
    This class defines the interface that all document processors must implement.
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
        Initialize the base processor.
        
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
    
    @abstractmethod
    def process(self, file_path: str) -> Document:
        """
        Process a document file and extract its content and structure.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            A Document object containing the extracted content
            
        Raises:
            ValueError: If the file cannot be processed
            FileNotFoundError: If the file doesn't exist
        """
        pass
    
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """
        Chunk a processed document into smaller, semantically meaningful parts.
        
        Args:
            document: The processed document to chunk
            
        Returns:
            A list of Chunk objects
        """
        pass
    
    def _generate_document_id(self, file_path: str) -> str:
        """
        Generate a unique ID for a document based on its path and attributes.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            A unique document ID
        """
        file_stats = os.stat(file_path)
        file_name = os.path.basename(file_path)
        
        # Create a deterministic ID based on file attributes
        # This way, the same file will get the same ID even across runs
        id_base = f"{file_name}-{file_stats.st_size}-{file_stats.st_mtime}"
        
        # Use the first 8 characters of the UUID generated from the id_base
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, id_base))[:8]
    
    def _chunk_text(self, text: str, document_id: str, chunk_type: str = Chunk.TYPE_TEXT) -> List[Chunk]:
        """
        Chunk text into smaller parts, respecting paragraph boundaries where possible.
        
        Args:
            text: The text to chunk
            document_id: ID of the source document
            chunk_type: Type of chunk being created
            
        Returns:
            A list of Chunk objects
        """
        if not text:
            return []
        
        # Split text into paragraphs
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk_text = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the chunk size and we already have content,
            # create a new chunk with what we have so far
            if current_chunk_text and len(current_chunk_text) + len(paragraph) > self.chunk_size:
                chunks.append(Chunk(
                    text=current_chunk_text.strip(),
                    metadata={
                        "type": chunk_type,
                        "document_id": document_id,
                    }
                ))
                
                # Start a new chunk, possibly including some overlap
                if self.chunk_overlap > 0 and len(current_chunk_text) > self.chunk_overlap:
                    # Extract the last part of the previous chunk for overlap
                    overlap_text = current_chunk_text[-self.chunk_overlap:]
                    current_chunk_text = overlap_text
                else:
                    current_chunk_text = ""
            
            # Add paragraph to current chunk
            if current_chunk_text:
                current_chunk_text += "\n\n" + paragraph
            else:
                current_chunk_text = paragraph
            
            # If this paragraph by itself is longer than chunk_size, we need to split it
            if len(paragraph) > self.chunk_size:
                # If we have accumulated other content, save it first
                if current_chunk_text != paragraph:
                    chunks.append(Chunk(
                        text=current_chunk_text[:-(len(paragraph))].strip(),
                        metadata={
                            "type": chunk_type,
                            "document_id": document_id,
                        }
                    ))
                
                # Now handle the large paragraph itself
                words = paragraph.split()
                current_chunk_text = ""
                
                for word in words:
                    if current_chunk_text and len(current_chunk_text) + len(word) + 1 > self.chunk_size:
                        chunks.append(Chunk(
                            text=current_chunk_text.strip(),
                            metadata={
                                "type": chunk_type,
                                "document_id": document_id,
                            }
                        ))
                        
                        # Start a new chunk with overlap
                        if self.chunk_overlap > 0 and len(current_chunk_text) > self.chunk_overlap:
                            current_chunk_text = current_chunk_text[-self.chunk_overlap:] + " " + word
                        else:
                            current_chunk_text = word
                    else:
                        if current_chunk_text:
                            current_chunk_text += " " + word
                        else:
                            current_chunk_text = word
                
                # Don't append the final segment yet, it will be handled at the end
            
        # Add the final chunk if there's anything left
        if current_chunk_text:
            chunks.append(Chunk(
                text=current_chunk_text.strip(),
                metadata={
                    "type": chunk_type,
                    "document_id": document_id,
                }
            ))
        
        return chunks