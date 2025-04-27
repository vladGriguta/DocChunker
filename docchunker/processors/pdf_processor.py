"""
Processor for PDF documents.
"""

import os
import re
import uuid
from typing import Dict, List, Optional, Tuple, Union

import pypdf
from pypdf import PdfReader

from docchunker.models.chunk import Chunk
from docchunker.models.document import Document
from docchunker.processors.base import BaseProcessor


class PdfProcessor(BaseProcessor):
    """
    Processor for PDF documents.
    
    This class handles the extraction and chunking of content from PDF files,
    with special handling for complex structures like tables and lists.
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
        Initialize the PDF processor.
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            preserve_structure: Whether to preserve document structure when chunking
            handle_tables: Whether to specially process tables
            handle_lists: Whether to specially process lists
            handle_images: Whether to extract and process images
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            preserve_structure=preserve_structure,
            handle_tables=handle_tables,
            handle_lists=handle_lists,
            handle_images=handle_images,
        )
    
    def process(self, file_path: str) -> Document:
        """
        Process a PDF document and extract its content and structure.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            A Document object containing the extracted content
            
        Raises:
            ValueError: If the file cannot be processed
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.lower().endswith(".pdf"):
            raise ValueError(f"File is not a PDF document: {file_path}")
        
        document_id = self._generate_document_id(file_path)
        
        try:
            # Fall back to basic PyPDF extraction
            return self._process_with_pypdf(file_path, document_id)
        
        except Exception as e:
            raise ValueError(f"Failed to process PDF document: {str(e)}")
    
    def _process_with_pypdf(self, file_path: str, document_id: str) -> Document:
        """
        Process a PDF using PyPDF.
        
        Args:
            file_path: Path to the PDF file
            document_id: ID for the document
            
        Returns:
            A Document object containing the extracted content
        """
        pdf_reader = PdfReader(file_path)
        metadata = self._extract_metadata_pypdf(pdf_reader)
        
        # Create our document model
        document = Document(
            document_id=document_id,
            file_path=file_path,
            metadata={
                "title": os.path.basename(file_path),
                "file_format": "pdf",
                "page_count": len(pdf_reader.pages),
                **metadata
            }
        )
        
        # Process each page
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            
            if not text:
                continue
            
            # Very basic structure detection - split by lines and look for patterns
            lines = text.split('\n')
            current_paragraph = []
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    # Empty line - end paragraph if we have one
                    if current_paragraph:
                        paragraph_text = ' '.join(current_paragraph)
                        self._process_text_block(paragraph_text, document, page_num + 1)
                        current_paragraph = []
                    continue
                
                # Check if this looks like a heading
                if self._is_likely_heading(line):
                    # End previous paragraph if any
                    if current_paragraph:
                        paragraph_text = ' '.join(current_paragraph)
                        self._process_text_block(paragraph_text, document, page_num + 1)
                        current_paragraph = []
                    
                    # Add the heading
                    level = self._estimate_heading_level(line)
                    document.chunks.append(Chunk.create_heading_chunk(
                        text=line,
                        document_id=document_id,
                        level=level,
                        page_number=page_num + 1
                    ))
                    continue
                
                # Check if this looks like a list item
                if self.handle_lists and self._is_likely_list_item(line):
                    # End previous paragraph if any
                    if current_paragraph:
                        paragraph_text = ' '.join(current_paragraph)
                        self._process_text_block(paragraph_text, document, page_num + 1)
                        current_paragraph = []
                    
                    # Add the list item
                    list_info = self._extract_list_info(line)
                    document.chunks.append(Chunk.create_list_chunk(
                        text=line,
                        document_id=document_id,
                        list_type=list_info["list_type"],
                        depth=list_info["depth"],
                        page_number=page_num + 1
                    ))
                    continue
                
                # If we reach here, treat as part of a paragraph
                current_paragraph.append(line)
            
            # Don't forget any remaining paragraph
            if current_paragraph:
                paragraph_text = ' '.join(current_paragraph)
                self._process_text_block(paragraph_text, document, page_num + 1)
        
        return document

    
    def chunk(self, document: Document) -> List[Chunk]:
        """
        Chunk a processed document into smaller, semantically meaningful parts.
        
        Args:
            document: The processed document to chunk
            
        Returns:
            A list of Chunk objects
        """
        # The chunking strategy is similar to the DocxProcessor
        result_chunks = []
        current_section_chunks = []
        current_section_text = ""
        current_section_type = None
        
        for chunk in document.chunks:
            chunk_type = chunk.metadata.get("type")
            
            # Handle special chunk types that should be preserved as-is
            if chunk_type in [Chunk.TYPE_TABLE, Chunk.TYPE_NESTED_TABLE, Chunk.TYPE_IMAGE, 
                             Chunk.TYPE_MERGED_CELL, Chunk.TYPE_EQUATION, Chunk.TYPE_CODE]:
                # First, add any accumulated section chunks
                if current_section_text:
                    section_chunks = self._chunk_text(
                        current_section_text, 
                        document.document_id, 
                        current_section_type or Chunk.TYPE_TEXT
                    )
                    result_chunks.extend(section_chunks)
                    current_section_text = ""
                    current_section_chunks = []
                    current_section_type = None
                
                # Then add the special chunk as-is
                result_chunks.append(chunk)
                continue
            
            # For heading chunks, they represent section boundaries
            if chunk_type == Chunk.TYPE_HEADING:
                # End previous section
                if current_section_text:
                    section_chunks = self._chunk_text(
                        current_section_text, 
                        document.document_id, 
                        current_section_type or Chunk.TYPE_TEXT
                    )
                    result_chunks.extend(section_chunks)
                
                # Start new section with the heading
                result_chunks.append(chunk)
                current_section_text = ""
                current_section_chunks = []
                current_section_type = Chunk.TYPE_TEXT
                continue
            
            # For regular text, lists, etc., accumulate into the current section
            if not current_section_type:
                current_section_type = chunk_type
            
            # If chunk would make section too large, chunk what we have so far
            if current_section_text and len(current_section_text) + len(chunk.text) > self.chunk_size * 2:
                section_chunks = self._chunk_text(
                    current_section_text, 
                    document.document_id, 
                    current_section_type
                )
                result_chunks.extend(section_chunks)
                current_section_text = chunk.text
                current_section_chunks = [chunk]
            else:
                if current_section_text:
                    current_section_text += "\n\n"
                current_section_text += chunk.text
                current_section_chunks.append(chunk)
        
        # Add any remaining section chunks
        if current_section_text:
            section_chunks = self._chunk_text(
                current_section_text, 
                document.document_id, 
                current_section_type or Chunk.TYPE_TEXT
            )
            result_chunks.extend(section_chunks)
        
        return result_chunks
    
    def _extract_metadata_pypdf(self, pdf_reader: PdfReader) -> Dict[str, str]:
        """
        Extract metadata from a PDF using PyPDF.
        
        Args:
            pdf_reader: The PyPDF PdfReader object
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Extract document info
        info = pdf_reader.metadata
        
        if info:
            if info.get("/Title"):
                metadata["title"] = info["/Title"]
            
            if info.get("/Author"):
                metadata["author"] = info["/Author"]
            
            if info.get("/CreationDate"):
                metadata["created_date"] = info["/CreationDate"]
            
            if info.get("/ModDate"):
                metadata["modified_date"] = info["/ModDate"]
        
        return metadata
    
    def _process_text_block(self, text: str, document: Document, page_number: int) -> None:
        """
        Process a block of text from a PDF.
        
        Args:
            text: The text to process
            document: The document to add chunks to
            page_number: The page number this text came from
        """
        # Check if this could be a table row (simple heuristic)
        if self.handle_tables and "|" in text and text.count("|") >= 2:
            # This might be a table row
            cells = [cell.strip() for cell in text.split("|")]
            
            # If all cells are non-empty and reasonable length, treat as table
            if all(cells) and all(len(cell) < 100 for cell in cells):
                table_id = f"table_p{page_number}_{len(document.chunks)}"
                
                document.chunks.append(Chunk(
                    text=text,
                    metadata={
                        "type": Chunk.TYPE_TABLE_CELL,
                        "document_id": document.document_id,
                        "table_id": table_id,
                        "page_number": page_number,
                    }
                ))
                return
        
        # Regular text chunk
        document.chunks.append(Chunk.create_text_chunk(
            text=text,
            document_id=document.document_id,
            page_number=page_number
        ))
    
    def _is_likely_heading(self, text: str) -> bool:
        """
        Check if text is likely to be a heading.
        
        Args:
            text: The text to check
            
        Returns:
            True if the text is likely a heading, False otherwise
        """
        # Very basic heuristics for heading detection
        if not text:
            return False
        
        # Check if text is short
        if len(text) < 100:
            # Check for common heading patterns
            if re.match(r'^[0-9]+\.', text) or re.match(r'^[A-Z][a-z]+ [0-9]+:', text):
                return True
            
            # Check if all caps or title case with no ending punctuation
            if text.isupper() or (text.istitle() and not text.rstrip()[-1] in ".,:;?!"):
                return True
            
            # Check for section/chapter indicators
            if re.match(r'^(Chapter|Section|Part|Appendix)\s+[0-9A-Z]', text, re.IGNORECASE):
                return True
        
        return False
    
    def _estimate_heading_level(self, text: str) -> int:
        """
        Estimate heading level from text.
        
        Args:
            text: The heading text
            
        Returns:
            Estimated heading level (1-6)
        """
        # Very basic heuristics for heading level estimation
        if not text:
            return 1
        
        # Check for numbered headings
        match = re.match(r'^([0-9]+)\.([0-9]+)?(\.([0-9]+))?', text)
        if match:
            if match.group(4):  # Matches pattern like 1.2.3
                return 3
            elif match.group(2):  # Matches pattern like 1.2
                return 2
            else:  # Matches pattern like 1.
                return 1
        
        # Check for Chapter/Section indicators
        if re.match(r'^Chapter\s+[0-9A-Z]', text, re.IGNORECASE):
            return 1
        if re.match(r'^Section\s+[0-9A-Z]', text, re.IGNORECASE):
            return 2
        
        # Based on length and case
        if text.isupper():
            return 1
        if text.istitle() and len(text) < 30:
            return 2
        if len(text) < 50:
            return 3
        
        return 4  # Default to level 4 for uncertain cases
    
    def _is_likely_list_item(self, text: str) -> bool:
        """
        Check if text is likely to be a list item.
        
        Args:
            text: The text to check
            
        Returns:
            True if the text is likely a list item, False otherwise
        """
        # Check for common list item patterns
        bullet_patterns = [
            r'^\s*[\•\-\*\>\◦\▪\■\○\●]\s',
            r'^\s*[0-9]+\.\s',
            r'^\s*[a-zA-Z]\.\s',
            r'^\s*[(][0-9a-zA-Z][)]\s',
            r'^\s*[ivxlcdm]+\.\s',
        ]
        
        for pattern in bullet_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _extract_list_info(self, text: str) -> Dict[str, Union[str, int]]:
        """
        Extract information about a list item.
        
        Args:
            text: The list item text
            
        Returns:
            Dictionary with list type and depth
        """
        # Default values
        info = {
            "list_type": "bullet",
            "depth": 0
        }
        
        # Try to determine depth from indentation
        indent_match = re.match(r'^(\s*)', text)
        if indent_match:
            indent = len(indent_match.group(1))
            info["depth"] = min(3, indent // 2)  # Approximation based on indent
        
        # Try to determine type from text pattern
        if re.match(r'^\s*[0-9]+\.', text) or re.match(r'^\s*[ivxlcdm]+\.', text) or re.match(r'^\s*[a-zA-Z]\.', text):
            info["list_type"] = "numbered"
        
        return info

    
    def _point_in_polygon(self, point, polygon) -> bool:
        """
        Check if a point is inside a polygon.
        
        Args:
            point: Point coordinates [x, y]
            polygon: List of point coordinates [[x1, y1], [x2, y2], ...]
            
        Returns:
            True if the point is inside the polygon, False otherwise
        """
        if not polygon or len(polygon) < 3:
            return False
        
        x, y = point[0], point[1]
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            x_intersect = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= x_intersect:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside