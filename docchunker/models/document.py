"""
Defines the Document class for representing parsed documents.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from docchunker.models.chunk import Chunk


@dataclass
class Document:
    """
    Represents a parsed document with its structural elements.
    
    Attributes:
        document_id: Unique identifier for the document
        file_path: Path to the source file
        metadata: Document metadata
        chunks: List of chunks extracted from the document
    """
    document_id: str
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Chunk] = field(default_factory=list)
    
    @property
    def title(self) -> Optional[str]:
        """Get the document title from metadata."""
        return self.metadata.get("title")
    
    @property
    def author(self) -> Optional[str]:
        """Get the document author from metadata."""
        return self.metadata.get("author")
    
    @property
    def created_date(self) -> Optional[str]:
        """Get the document creation date from metadata."""
        return self.metadata.get("created_date")
    
    @property
    def modified_date(self) -> Optional[str]:
        """Get the document last modified date from metadata."""
        return self.metadata.get("modified_date")
    
    @property
    def page_count(self) -> Optional[int]:
        """Get the document page count from metadata."""
        return self.metadata.get("page_count")
    
    @property
    def file_format(self) -> Optional[str]:
        """Get the document file format from metadata."""
        return self.metadata.get("file_format")
    
    @property
    def has_tables(self) -> bool:
        """Check if the document contains tables."""
        return any(chunk.metadata.get("type") in 
                  [Chunk.TYPE_TABLE, Chunk.TYPE_NESTED_TABLE, Chunk.TYPE_TABLE_CELL, Chunk.TYPE_MERGED_CELL] 
                  for chunk in self.chunks)
    
    @property
    def has_lists(self) -> bool:
        """Check if the document contains lists."""
        return any(chunk.metadata.get("type") == Chunk.TYPE_LIST for chunk in self.chunks)
    
    @property
    def has_images(self) -> bool:
        """Check if the document contains images."""
        return any(chunk.metadata.get("type") == Chunk.TYPE_IMAGE for chunk in self.chunks)
    
    @property
    def table_count(self) -> int:
        """Count the number of tables in the document."""
        table_ids = set()
        for chunk in self.chunks:
            if chunk.metadata.get("type") == Chunk.TYPE_TABLE:
                table_ids.add(chunk.metadata.get("table_id"))
        return len(table_ids)
    
    @property
    def image_count(self) -> int:
        """Count the number of images in the document."""
        image_ids = set()
        for chunk in self.chunks:
            if chunk.metadata.get("type") == Chunk.TYPE_IMAGE:
                image_ids.add(chunk.metadata.get("image_id"))
        return len(image_ids)
    
    def get_chunks_by_type(self, chunk_type: str) -> List[Chunk]:
        """
        Get all chunks of a specific type.
        
        Args:
            chunk_type: The type of chunks to retrieve
            
        Returns:
            List of chunks matching the specified type
        """
        return [chunk for chunk in self.chunks if chunk.metadata.get("type") == chunk_type]
    
    def get_chunks_by_page(self, page_number: int) -> List[Chunk]:
        """
        Get all chunks from a specific page.
        
        Args:
            page_number: The page number to filter by
            
        Returns:
            List of chunks from the specified page
        """
        return [chunk for chunk in self.chunks if chunk.metadata.get("page_number") == page_number]
    
    def get_table_chunks(self, table_id: Optional[str] = None) -> List[Chunk]:
        """
        Get all table-related chunks, optionally filtering by table ID.
        
        Args:
            table_id: Optional table ID to filter by
            
        Returns:
            List of table-related chunks
        """
        table_types = [Chunk.TYPE_TABLE, Chunk.TYPE_NESTED_TABLE, Chunk.TYPE_TABLE_CELL, Chunk.TYPE_MERGED_CELL]
        
        if table_id:
            return [chunk for chunk in self.chunks 
                   if chunk.metadata.get("type") in table_types 
                   and chunk.metadata.get("table_id") == table_id]
        else:
            return [chunk for chunk in self.chunks if chunk.metadata.get("type") in table_types]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the document to a dictionary.
        
        Returns:
            Dictionary representation of the document
        """
        return {
            "document_id": self.document_id,
            "file_path": self.file_path,
            "metadata": self.metadata,
            "chunks": [
                {
                    "text": chunk.text,
                    "metadata": chunk.metadata
                }
                for chunk in self.chunks
            ]
        }