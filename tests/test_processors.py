import pytest
from pathlib import Path
from typing import List
import os

from docchunker.processors.docx_processor import DocxProcessor
from docchunker.processors.pdf_processor import PdfProcessor
from docchunker.models.chunk import Chunk
from docchunker.models.document import Document


class TestDocxProcessor:
    """Test cases for the DocxProcessor class."""
    
    def test_initialization(self):
        """Test DocxProcessor initialization."""
        processor = DocxProcessor()
        
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.preserve_structure is True
        assert processor.handle_tables is True
        assert processor.handle_lists is True
        assert processor.handle_images is False
    
    def test_process_valid_docx(self, sample_docx_path: Path):
        """Test processing a valid DOCX file."""
        processor = DocxProcessor()
        document = processor.process(str(sample_docx_path))
        
        assert isinstance(document, Document)
        assert document.file_path == str(sample_docx_path)
        assert document.metadata["file_format"] == "docx"
        assert document.metadata["title"] == os.path.basename(str(sample_docx_path))
        assert len(document.chunks) > 0
    
    def test_process_invalid_file(self, temp_dir: Path):
        """Test processing an invalid file."""
        processor = DocxProcessor()
        
        # Non-existent file
        with pytest.raises(FileNotFoundError):
            processor.process("non_existent.docx")
        
        # Wrong file type
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("This is a text file")
        
        with pytest.raises(ValueError, match="not a DOCX document"):
            processor.process(str(txt_file))
    
    def test_extract_headings(self, sample_docx_path: Path):
        """Test that headings are properly extracted."""
        processor = DocxProcessor()
        document = processor.process(str(sample_docx_path))
        
        heading_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_HEADING]
        assert len(heading_chunks) > 0
        
        # Check heading levels
        for chunk in heading_chunks:
            assert "level" in chunk.metadata
            assert 0 <= chunk.metadata["level"] <= 6
    
    def test_extract_lists(self, sample_docx_path: Path):
        """Test that lists are properly extracted."""
        processor = DocxProcessor(handle_lists=True)
        document = processor.process(str(sample_docx_path))
        
        list_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_LIST]
        assert len(list_chunks) > 0
        
        # Check list metadata
        for chunk in list_chunks:
            assert "list_type" in chunk.metadata
            assert chunk.metadata["list_type"] in ["bullet", "numbered"]
            assert "depth" in chunk.metadata
            assert chunk.metadata["depth"] >= 0
    
    def test_extract_tables(self, sample_docx_path: Path):
        """Test that tables are properly extracted."""
        processor = DocxProcessor(handle_tables=True)
        document = processor.process(str(sample_docx_path))
        
        table_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_TABLE]
        assert len(table_chunks) > 0
        
        # Check table metadata
        for chunk in table_chunks:
            assert "table_id" in chunk.metadata
            assert "rows" in chunk.metadata
            assert "columns" in chunk.metadata
            assert chunk.metadata["rows"] > 0
            assert chunk.metadata["columns"] > 0
    
    def test_extract_table_cells(self, sample_docx_path: Path):
        """Test that table cells are properly extracted."""
        processor = DocxProcessor(handle_tables=True)
        document = processor.process(str(sample_docx_path))
        
        cell_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_TABLE_CELL]
        
        # Should have cells if tables are handled
        if processor.handle_tables:
            assert len(cell_chunks) > 0
            
            # Check cell metadata
            for chunk in cell_chunks:
                assert "table_id" in chunk.metadata
                assert "row" in chunk.metadata
                assert "column" in chunk.metadata
                assert chunk.metadata["row"] >= 0
                assert chunk.metadata["column"] >= 0
    
    def test_chunk_generation(self, sample_docx_path: Path):
        """Test the chunking process."""
        processor = DocxProcessor(chunk_size=100, chunk_overlap=20)
        document = processor.process(str(sample_docx_path))
        chunks = processor.chunk(document)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        
        # Check that text chunks respect size limits (approximately)
        text_chunks = [c for c in chunks if c.metadata.get("type") == Chunk.TYPE_TEXT]
        for chunk in text_chunks:
            # Allow some flexibility for paragraph boundaries
            assert len(chunk.text) <= processor.chunk_size * 2
    
    def test_handle_tables_disabled(self, sample_docx_path: Path):
        """Test behavior when table handling is disabled."""
        processor = DocxProcessor(handle_tables=False)
        document = processor.process(str(sample_docx_path))
        
        # Should not have table-specific chunks
        table_specific_types = [
            Chunk.TYPE_TABLE_CELL,
            Chunk.TYPE_MERGED_CELL,
            Chunk.TYPE_NESTED_TABLE
        ]
        
        specific_chunks = [c for c in document.chunks 
                          if c.metadata.get("type") in table_specific_types]
        assert len(specific_chunks) == 0
    
    def test_handle_lists_disabled(self, sample_docx_path: Path):
        """Test behavior when list handling is disabled."""
        processor = DocxProcessor(handle_lists=False)
        document = processor.process(str(sample_docx_path))
        
        # Should not have list chunks
        list_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_LIST]
        assert len(list_chunks) == 0
    
    def test_complex_document_processing(self, complex_docx_path: Path):
        """Test processing a complex document."""
        processor = DocxProcessor()
        document = processor.process(str(complex_docx_path))
        chunks = processor.chunk(document)
        
        # Check various aspects of complex document processing
        assert len(chunks) > 0
        
        # Check for multiple heading levels
        heading_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_HEADING]
        heading_levels = {c.metadata.get("level") for c in heading_chunks}
        assert len(heading_levels) >= 2
        
        # Check for merged cells (if present in the document)
        merged_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_MERGED_CELL]
        for chunk in merged_chunks:
            assert "row_span" in chunk.metadata
            assert "col_span" in chunk.metadata
    
    def test_metadata_extraction(self, sample_docx_path: Path):
        """Test document metadata extraction."""
        processor = DocxProcessor()
        document = processor.process(str(sample_docx_path))
        
        # Check basic metadata
        assert "title" in document.metadata
        assert "file_format" in document.metadata
        assert document.metadata["file_format"] == "docx"
        
        # Page count should be estimated
        if "page_count" in document.metadata:
            assert document.metadata["page_count"] > 0


class TestPdfProcessor:
    """Test cases for the PdfProcessor class."""
    
    def test_initialization(self):
        """Test PdfProcessor initialization."""
        processor = PdfProcessor()
        
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.preserve_structure is True
        assert processor.handle_tables is True
        assert processor.handle_lists is True
        assert processor.handle_images is False
    
    def test_process_valid_pdf(self, sample_pdf_path: Path):
        """Test processing a valid PDF file."""
        processor = PdfProcessor()
        document = processor.process(str(sample_pdf_path))
        
        assert isinstance(document, Document)
        assert document.file_path == str(sample_pdf_path)
        assert document.metadata["file_format"] == "pdf"
        assert document.metadata["title"] == os.path.basename(str(sample_pdf_path))
        assert len(document.chunks) > 0
    
    def test_process_invalid_file(self, temp_dir: Path):
        """Test processing an invalid file."""
        processor = PdfProcessor()
        
        # Non-existent file
        with pytest.raises(FileNotFoundError):
            processor.process("non_existent.pdf")
        
        # Wrong file type
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("This is a text file")
        
        with pytest.raises(ValueError, match="not a PDF document"):
            processor.process(str(txt_file))
    
    def test_extract_text(self, sample_pdf_path: Path):
        """Test that text is properly extracted from PDF."""
        processor = PdfProcessor()
        document = processor.process(str(sample_pdf_path))
        
        # Should have extracted some text
        assert len(document.chunks) > 0
        
        # Check that chunks have text
        for chunk in document.chunks:
            assert chunk.text
            assert len(chunk.text.strip()) > 0
    
    def test_page_number_tracking(self, sample_pdf_path: Path):
        """Test that page numbers are tracked correctly."""
        processor = PdfProcessor()
        document = processor.process(str(sample_pdf_path))
        
        # Check that chunks have page numbers
        for chunk in document.chunks:
            if "page_number" in chunk.metadata:
                assert chunk.metadata["page_number"] > 0
    
    def test_heading_detection(self, sample_pdf_path: Path):
        """Test basic heading detection in PDFs."""
        processor = PdfProcessor()
        document = processor.process(str(sample_pdf_path))
        
        # Check if any headings were detected
        heading_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_HEADING]
        
        # PDF heading detection is heuristic-based, so we just check the structure
        for chunk in heading_chunks:
            assert "level" in chunk.metadata
            assert 1 <= chunk.metadata["level"] <= 6
    
    def test_list_detection(self, sample_pdf_path: Path):
        """Test basic list detection in PDFs."""
        processor = PdfProcessor(handle_lists=True)
        document = processor.process(str(sample_pdf_path))
        
        # Check if any lists were detected
        list_chunks = [c for c in document.chunks if c.metadata.get("type") == Chunk.TYPE_LIST]
        
        # PDF list detection is heuristic-based
        for chunk in list_chunks:
            assert "list_type" in chunk.metadata
            assert "depth" in chunk.metadata
    
    def test_chunk_generation(self, sample_pdf_path: Path):
        """Test the chunking process for PDFs."""
        processor = PdfProcessor(chunk_size=100, chunk_overlap=20)
        document = processor.process(str(sample_pdf_path))
        chunks = processor.chunk(document)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
    
    def test_metadata_extraction(self, sample_pdf_path: Path):
        """Test PDF metadata extraction."""
        processor = PdfProcessor()
        document = processor.process(str(sample_pdf_path))
        
        # Check basic metadata
        assert "title" in document.metadata
        assert "file_format" in document.metadata
        assert document.metadata["file_format"] == "pdf"
        
        # Check page count
        if "page_count" in document.metadata:
            assert document.metadata["page_count"] > 0
    
    def test_table_detection(self, sample_pdf_path: Path):
        """Test basic table detection in PDFs."""
        processor = PdfProcessor(handle_tables=True)
        document = processor.process(str(sample_pdf_path))
        
        # PDF table detection is very basic and heuristic-based
        # Just check that the processor doesn't crash and produces valid chunks
        table_related_chunks = [c for c in document.chunks 
                               if c.metadata.get("type") in [Chunk.TYPE_TABLE, Chunk.TYPE_TABLE_CELL]]
        
        # All chunks should have valid metadata
        for chunk in table_related_chunks:
            assert "document_id" in chunk.metadata
            assert chunk.text is not None