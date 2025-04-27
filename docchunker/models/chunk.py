"""
Defines the Chunk class for representing document fragments.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Chunk:
    """
    Represents a chunk of text from a document with metadata.
    
    Attributes:
        text: The text content of the chunk
        metadata: Metadata about the chunk and its source
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Type constants
    TYPE_TEXT = "text"
    TYPE_HEADING = "heading"
    TYPE_LIST = "list"
    TYPE_TABLE = "table"
    TYPE_IMAGE = "image"
    TYPE_EQUATION = "equation"
    TYPE_CODE = "code"
    TYPE_NESTED_TABLE = "nested_table"
    TYPE_TABLE_CELL = "table_cell"
    TYPE_MERGED_CELL = "merged_cell"
    TYPE_FOOTER = "footer"
    TYPE_HEADER = "header"
    TYPE_FOOTNOTE = "footnote"
    
    @classmethod
    def create_text_chunk(
        cls, 
        text: str, 
        document_id: str, 
        page_number: Optional[int] = None, 
        paragraph_index: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk of regular text.
        
        Args:
            text: The text content
            document_id: ID of the source document
            page_number: Optional page number
            paragraph_index: Optional paragraph index
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_TEXT,
                "document_id": document_id,
                "page_number": page_number,
                "paragraph_index": paragraph_index,
            }
        )
    
    @classmethod
    def create_heading_chunk(
        cls, 
        text: str, 
        document_id: str, 
        level: int, 
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from a heading.
        
        Args:
            text: The heading text
            document_id: ID of the source document
            level: Heading level (1-6)
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_HEADING,
                "document_id": document_id,
                "page_number": page_number,
                "level": level,
            }
        )
    
    @classmethod
    def create_list_chunk(
        cls, 
        text: str, 
        document_id: str, 
        list_type: str, 
        depth: int, 
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from a list item.
        
        Args:
            text: The list item text including any markers
            document_id: ID of the source document
            list_type: Type of list (e.g., "bullet", "numbered")
            depth: Nesting level of the list item
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_LIST,
                "document_id": document_id,
                "page_number": page_number,
                "list_type": list_type,
                "depth": depth,
            }
        )
    
    @classmethod
    def create_table_chunk(
        cls, 
        text: str, 
        document_id: str, 
        table_id: str, 
        rows: int, 
        columns: int, 
        has_header: bool = False, 
        has_merged_cells: bool = False,
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from a table.
        
        Args:
            text: The textual representation of the table
            document_id: ID of the source document
            table_id: ID of the table within the document
            rows: Number of rows in the table
            columns: Number of columns in the table
            has_header: Whether the table has a header row
            has_merged_cells: Whether the table has merged cells
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_TABLE,
                "document_id": document_id,
                "page_number": page_number,
                "table_id": table_id,
                "rows": rows,
                "columns": columns,
                "has_header": has_header,
                "has_merged_cells": has_merged_cells,
            }
        )
    
    @classmethod
    def create_nested_table_chunk(
        cls, 
        text: str, 
        document_id: str, 
        table_id: str, 
        parent_table_id: str,
        rows: int, 
        columns: int, 
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from a nested table.
        
        Args:
            text: The textual representation of the table
            document_id: ID of the source document
            table_id: ID of the table within the document
            parent_table_id: ID of the parent table
            rows: Number of rows in the table
            columns: Number of columns in the table
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_NESTED_TABLE,
                "document_id": document_id,
                "page_number": page_number,
                "table_id": table_id,
                "parent_table_id": parent_table_id,
                "rows": rows,
                "columns": columns,
            }
        )
    
    @classmethod
    def create_image_chunk(
        cls, 
        text: str, 
        document_id: str, 
        image_id: str, 
        caption: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from an image.
        
        Args:
            text: The image description or caption
            document_id: ID of the source document
            image_id: ID of the image within the document
            caption: Optional image caption
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_IMAGE,
                "document_id": document_id,
                "page_number": page_number,
                "image_id": image_id,
                "caption": caption,
            }
        )
    
    @classmethod
    def create_merged_cell_chunk(
        cls, 
        text: str, 
        document_id: str, 
        table_id: str, 
        row_span: int, 
        col_span: int, 
        start_row: int, 
        start_col: int,
        page_number: Optional[int] = None
    ) -> "Chunk":
        """
        Create a chunk from a merged cell.
        
        Args:
            text: The cell content
            document_id: ID of the source document
            table_id: ID of the table containing the cell
            row_span: Number of rows the cell spans
            col_span: Number of columns the cell spans
            start_row: Starting row index
            start_col: Starting column index
            page_number: Optional page number
            
        Returns:
            A new Chunk instance
        """
        return cls(
            text=text,
            metadata={
                "type": cls.TYPE_MERGED_CELL,
                "document_id": document_id,
                "page_number": page_number,
                "table_id": table_id,
                "row_span": row_span,
                "col_span": col_span,
                "start_row": start_row,
                "start_col": start_col,
            }
        )