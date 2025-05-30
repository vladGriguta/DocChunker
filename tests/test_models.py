import pytest
from typing import Dict, Any

from docchunker.models.chunk import Chunk
from docchunker.models.document import Document


class TestChunk:
    """Test cases for the Chunk class."""
    
    def test_chunk_creation_basic(self):
        """Test basic chunk creation."""
        chunk = Chunk(
            text="This is a test chunk",
            metadata={"type": "text", "document_id": "doc123"}
        )
        
        assert chunk.text == "This is a test chunk"
        assert chunk.metadata["type"] == "text"
        assert chunk.metadata["document_id"] == "doc123"
    
    def test_create_text_chunk(self):
        """Test creating a text chunk using factory method."""
        chunk = Chunk.create_text_chunk(
            text="Sample text",
            document_id="doc123",
            page_number=1,
            paragraph_index=0
        )
        
        assert chunk.text == "Sample text"
        assert chunk.metadata["type"] == Chunk.TYPE_TEXT
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["page_number"] == 1
        assert chunk.metadata["paragraph_index"] == 0
    
    def test_create_heading_chunk(self):
        """Test creating a heading chunk using factory method."""
        chunk = Chunk.create_heading_chunk(
            text="Chapter 1",
            document_id="doc123",
            level=1,
            page_number=1
        )
        
        assert chunk.text == "Chapter 1"
        assert chunk.metadata["type"] == Chunk.TYPE_HEADING
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["level"] == 1
        assert chunk.metadata["page_number"] == 1
    
    def test_create_list_chunk(self):
        """Test creating a list chunk using factory method."""
        chunk = Chunk.create_list_chunk(
            text="• First item",
            document_id="doc123",
            list_type="bullet",
            depth=0,
            page_number=2
        )
        
        assert chunk.text == "• First item"
        assert chunk.metadata["type"] == Chunk.TYPE_LIST
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["list_type"] == "bullet"
        assert chunk.metadata["depth"] == 0
        assert chunk.metadata["page_number"] == 2
    
    def test_create_table_chunk(self):
        """Test creating a table chunk using factory method."""
        chunk = Chunk.create_table_chunk(
            text="Header1 | Header2\nData1 | Data2",
            document_id="doc123",
            table_id="table1",
            rows=2,
            columns=2,
            has_header=True,
            has_merged_cells=False,
            page_number=3
        )
        
        assert chunk.text == "Header1 | Header2\nData1 | Data2"
        assert chunk.metadata["type"] == Chunk.TYPE_TABLE
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["table_id"] == "table1"
        assert chunk.metadata["rows"] == 2
        assert chunk.metadata["columns"] == 2
        assert chunk.metadata["has_header"] is True
        assert chunk.metadata["has_merged_cells"] is False
        assert chunk.metadata["page_number"] == 3
    
    def test_create_nested_table_chunk(self):
        """Test creating a nested table chunk using factory method."""
        chunk = Chunk.create_nested_table_chunk(
            text="Nested table content",
            document_id="doc123",
            table_id="nested1",
            parent_table_id="parent1",
            rows=1,
            columns=1,
            page_number=4
        )
        
        assert chunk.text == "Nested table content"
        assert chunk.metadata["type"] == Chunk.TYPE_NESTED_TABLE
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["table_id"] == "nested1"
        assert chunk.metadata["parent_table_id"] == "parent1"
        assert chunk.metadata["rows"] == 1
        assert chunk.metadata["columns"] == 1
        assert chunk.metadata["page_number"] == 4
    
    def test_create_image_chunk(self):
        """Test creating an image chunk using factory method."""
        chunk = Chunk.create_image_chunk(
            text="Image of a diagram",
            document_id="doc123",
            image_id="img1",
            caption="Figure 1: System Architecture",
            page_number=5
        )
        
        assert chunk.text == "Image of a diagram"
        assert chunk.metadata["type"] == Chunk.TYPE_IMAGE
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["image_id"] == "img1"
        assert chunk.metadata["caption"] == "Figure 1: System Architecture"
        assert chunk.metadata["page_number"] == 5
    
    def test_create_merged_cell_chunk(self):
        """Test creating a merged cell chunk using factory method."""
        chunk = Chunk.create_merged_cell_chunk(
            text="Merged cell content",
            document_id="doc123",
            table_id="table1",
            row_span=2,
            col_span=3,
            start_row=0,
            start_col=0,
            page_number=6
        )
        
        assert chunk.text == "Merged cell content"
        assert chunk.metadata["type"] == Chunk.TYPE_MERGED_CELL
        assert chunk.metadata["document_id"] == "doc123"
        assert chunk.metadata["table_id"] == "table1"
        assert chunk.metadata["row_span"] == 2
        assert chunk.metadata["col_span"] == 3
        assert chunk.metadata["start_row"] == 0
        assert chunk.metadata["start_col"] == 0
        assert chunk.metadata["page_number"] == 6
    
    def test_chunk_type_constants(self):
        """Test that all chunk type constants are defined."""
        assert Chunk.TYPE_TEXT == "text"
        assert Chunk.TYPE_HEADING == "heading"
        assert Chunk.TYPE_LIST == "list"
        assert Chunk.TYPE_TABLE == "table"
        assert Chunk.TYPE_IMAGE == "image"
        assert Chunk.TYPE_EQUATION == "equation"
        assert Chunk.TYPE_CODE == "code"
        assert Chunk.TYPE_NESTED_TABLE == "nested_table"
        assert Chunk.TYPE_TABLE_CELL == "table_cell"
        assert Chunk.TYPE_MERGED_CELL == "merged_cell"
        assert Chunk.TYPE_FOOTER == "footer"
        assert Chunk.TYPE_HEADER == "header"
        assert Chunk.TYPE_FOOTNOTE == "footnote"


class TestDocument:
    """Test cases for the Document class."""
    
    def test_document_creation_basic(self):
        """Test basic document creation."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx",
            metadata={"title": "Test Document", "author": "Test Author"}
        )
        
        assert doc.document_id == "doc123"
        assert doc.file_path == "/path/to/document.docx"
        assert doc.metadata["title"] == "Test Document"
        assert doc.metadata["author"] == "Test Author"
        assert doc.chunks == []
    
    def test_document_properties(self):
        """Test document property accessors."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx",
            metadata={
                "title": "Test Title",
                "author": "Test Author",
                "created_date": "2024-01-01",
                "modified_date": "2024-01-02",
                "page_count": 10,
                "file_format": "docx"
            }
        )
        
        assert doc.title == "Test Title"
        assert doc.author == "Test Author"
        assert doc.created_date == "2024-01-01"
        assert doc.modified_date == "2024-01-02"
        assert doc.page_count == 10
        assert doc.file_format == "docx"
    
    def test_document_properties_missing(self):
        """Test document property accessors with missing metadata."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        assert doc.title is None
        assert doc.author is None
        assert doc.created_date is None
        assert doc.modified_date is None
        assert doc.page_count is None
        assert doc.file_format is None
    
    def test_has_tables(self):
        """Test the has_tables property."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Initially no tables
        assert doc.has_tables is False
        
        # Add a table chunk
        doc.chunks.append(Chunk(
            text="Table content",
            metadata={"type": Chunk.TYPE_TABLE, "document_id": "doc123"}
        ))
        
        assert doc.has_tables is True
        
        # Also test with table cell
        doc2 = Document(
            document_id="doc124",
            file_path="/path/to/document2.docx"
        )
        doc2.chunks.append(Chunk(
            text="Cell content",
            metadata={"type": Chunk.TYPE_TABLE_CELL, "document_id": "doc124"}
        ))
        
        assert doc2.has_tables is True
    
    def test_has_lists(self):
        """Test the has_lists property."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Initially no lists
        assert doc.has_lists is False
        
        # Add a list chunk
        doc.chunks.append(Chunk(
            text="List item",
            metadata={"type": Chunk.TYPE_LIST, "document_id": "doc123"}
        ))
        
        assert doc.has_lists is True
    
    def test_has_images(self):
        """Test the has_images property."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Initially no images
        assert doc.has_images is False
        
        # Add an image chunk
        doc.chunks.append(Chunk(
            text="Image description",
            metadata={"type": Chunk.TYPE_IMAGE, "document_id": "doc123"}
        ))
        
        assert doc.has_images is True
    
    def test_table_count(self):
        """Test the table_count property."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Initially no tables
        assert doc.table_count == 0
        
        # Add table chunks with different IDs
        doc.chunks.append(Chunk(
            text="Table 1",
            metadata={"type": Chunk.TYPE_TABLE, "document_id": "doc123", "table_id": "table1"}
        ))
        doc.chunks.append(Chunk(
            text="Table 2",
            metadata={"type": Chunk.TYPE_TABLE, "document_id": "doc123", "table_id": "table2"}
        ))
        
        # Add another chunk for the same table (shouldn't increase count)
        doc.chunks.append(Chunk(
            text="Table 1 again",
            metadata={"type": Chunk.TYPE_TABLE, "document_id": "doc123", "table_id": "table1"}
        ))
        
        assert doc.table_count == 2
    
    def test_image_count(self):
        """Test the image_count property."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Initially no images
        assert doc.image_count == 0
        
        # Add image chunks with different IDs
        doc.chunks.append(Chunk(
            text="Image 1",
            metadata={"type": Chunk.TYPE_IMAGE, "document_id": "doc123", "image_id": "img1"}
        ))
        doc.chunks.append(Chunk(
            text="Image 2",
            metadata={"type": Chunk.TYPE_IMAGE, "document_id": "doc123", "image_id": "img2"}
        ))
        
        # Add another chunk for the same image (shouldn't increase count)
        doc.chunks.append(Chunk(
            text="Image 1 again",
            metadata={"type": Chunk.TYPE_IMAGE, "document_id": "doc123", "image_id": "img1"}
        ))
        
        assert doc.image_count == 2
    
    def test_get_chunks_by_type(self):
        """Test getting chunks by type."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Add various types of chunks
        doc.chunks.append(Chunk(
            text="Text 1",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123"}
        ))
        doc.chunks.append(Chunk(
            text="Heading 1",
            metadata={"type": Chunk.TYPE_HEADING, "document_id": "doc123"}
        ))
        doc.chunks.append(Chunk(
            text="Text 2",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123"}
        ))
        doc.chunks.append(Chunk(
            text="List item",
            metadata={"type": Chunk.TYPE_LIST, "document_id": "doc123"}
        ))
        
        # Get chunks by type
        text_chunks = doc.get_chunks_by_type(Chunk.TYPE_TEXT)
        assert len(text_chunks) == 2
        assert all(c.metadata["type"] == Chunk.TYPE_TEXT for c in text_chunks)
        
        heading_chunks = doc.get_chunks_by_type(Chunk.TYPE_HEADING)
        assert len(heading_chunks) == 1
        assert heading_chunks[0].text == "Heading 1"
        
        list_chunks = doc.get_chunks_by_type(Chunk.TYPE_LIST)
        assert len(list_chunks) == 1
        assert list_chunks[0].text == "List item"
        
        # Non-existent type
        image_chunks = doc.get_chunks_by_type(Chunk.TYPE_IMAGE)
        assert len(image_chunks) == 0
    
    def test_get_chunks_by_page(self):
        """Test getting chunks by page number."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Add chunks from different pages
        doc.chunks.append(Chunk(
            text="Page 1 text",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123", "page_number": 1}
        ))
        doc.chunks.append(Chunk(
            text="Page 2 text",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123", "page_number": 2}
        ))
        doc.chunks.append(Chunk(
            text="Another page 1 text",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123", "page_number": 1}
        ))
        doc.chunks.append(Chunk(
            text="No page number",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123"}
        ))
        
        # Get chunks by page
        page1_chunks = doc.get_chunks_by_page(1)
        assert len(page1_chunks) == 2
        assert all(c.metadata.get("page_number") == 1 for c in page1_chunks)
        
        page2_chunks = doc.get_chunks_by_page(2)
        assert len(page2_chunks) == 1
        assert page2_chunks[0].text == "Page 2 text"
        
        # Non-existent page
        page3_chunks = doc.get_chunks_by_page(3)
        assert len(page3_chunks) == 0
    
    def test_get_table_chunks(self):
        """Test getting table-related chunks."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx"
        )
        
        # Add various chunks
        doc.chunks.append(Chunk(
            text="Table 1",
            metadata={"type": Chunk.TYPE_TABLE, "document_id": "doc123", "table_id": "table1"}
        ))
        doc.chunks.append(Chunk(
            text="Cell 1",
            metadata={"type": Chunk.TYPE_TABLE_CELL, "document_id": "doc123", "table_id": "table1"}
        ))
        doc.chunks.append(Chunk(
            text="Cell 2",
            metadata={"type": Chunk.TYPE_TABLE_CELL, "document_id": "doc123", "table_id": "table2"}
        ))
        doc.chunks.append(Chunk(
            text="Merged cell",
            metadata={"type": Chunk.TYPE_MERGED_CELL, "document_id": "doc123", "table_id": "table1"}
        ))
        doc.chunks.append(Chunk(
            text="Regular text",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123"}
        ))
        
        # Get all table chunks
        all_table_chunks = doc.get_table_chunks()
        assert len(all_table_chunks) == 4
        
        # Get chunks for specific table
        table1_chunks = doc.get_table_chunks("table1")
        assert len(table1_chunks) == 3
        assert all(c.metadata.get("table_id") == "table1" for c in table1_chunks)
        
        table2_chunks = doc.get_table_chunks("table2")
        assert len(table2_chunks) == 1
        assert table2_chunks[0].text == "Cell 2"
    
    def test_to_dict(self):
        """Test converting document to dictionary."""
        doc = Document(
            document_id="doc123",
            file_path="/path/to/document.docx",
            metadata={"title": "Test Document", "author": "Test Author"}
        )
        
        # Add some chunks
        doc.chunks.append(Chunk(
            text="Text chunk",
            metadata={"type": Chunk.TYPE_TEXT, "document_id": "doc123"}
        ))
        doc.chunks.append(Chunk(
            text="Heading chunk",
            metadata={"type": Chunk.TYPE_HEADING, "document_id": "doc123", "level": 1}
        ))
        
        # Convert to dict
        doc_dict = doc.to_dict()
        
        assert doc_dict["document_id"] == "doc123"
        assert doc_dict["file_path"] == "/path/to/document.docx"
        assert doc_dict["metadata"]["title"] == "Test Document"
        assert doc_dict["metadata"]["author"] == "Test Author"
        
        assert len(doc_dict["chunks"]) == 2
        assert doc_dict["chunks"][0]["text"] == "Text chunk"
        assert doc_dict["chunks"][0]["metadata"]["type"] == Chunk.TYPE_TEXT
        assert doc_dict["chunks"][1]["text"] == "Heading chunk"
        assert doc_dict["chunks"][1]["metadata"]["type"] == Chunk.TYPE_HEADING
        assert doc_dict["chunks"][1]["metadata"]["level"] == 1