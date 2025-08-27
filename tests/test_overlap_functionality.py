import pytest
from pathlib import Path
from docchunker import DocChunker
from docchunker.processors.document_chunker import DocumentChunker


def test_overlapping_elements_basic_functionality():
    """Test that overlapping elements can be initialized without error."""
    # Should not raise NotImplementedError anymore
    chunker_no_overlap = DocChunker(chunk_size=100, num_overlapping_elements=0)
    chunker_with_overlap = DocChunker(chunk_size=100, num_overlapping_elements=2)
    
    assert chunker_no_overlap.processors["docx"].chunker.num_overlapping_elements == 0
    assert chunker_with_overlap.processors["docx"].chunker.num_overlapping_elements == 2


def test_overlap_metadata_fields():
    """Test that overlap metadata fields are correctly set."""
    # Use a small chunk size to force splitting
    chunker = DocChunker(chunk_size=50, num_overlapping_elements=1)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    chunks = chunker.process_document(str(test_file))
    
    # Find chunks that should have overlap metadata
    list_chunks = [c for c in chunks if c.metadata.get("node_type") == "list_container"]
    
    if len(list_chunks) > 1:  # Only test if we have multiple list chunks
        # First chunk should not have overlap
        first_chunk = list_chunks[0]
        assert first_chunk.metadata.get("has_overlap", False) == False
        assert first_chunk.metadata.get("overlap_elements", 0) == 0
        
        # Subsequent chunks should have overlap if num_overlapping_elements > 0
        for chunk in list_chunks[1:]:
            assert "has_overlap" in chunk.metadata
            assert "overlap_elements" in chunk.metadata
            if chunker.processors["docx"].chunker.num_overlapping_elements > 0:
                assert chunk.metadata["has_overlap"] == True
                assert chunk.metadata["overlap_elements"] > 0


def test_overlap_with_different_sizes():
    """Test overlapping with different overlap sizes."""
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Test with no overlap
    chunker_no_overlap = DocChunker(chunk_size=50, num_overlapping_elements=0)
    chunks_no_overlap = chunker_no_overlap.process_document(str(test_file))
    
    # Test with overlap
    chunker_with_overlap = DocChunker(chunk_size=50, num_overlapping_elements=2)
    chunks_with_overlap = chunker_with_overlap.process_document(str(test_file))
    
    # With overlap, we might have more chunks due to repeated content
    # but this depends on the document structure
    assert len(chunks_no_overlap) > 0
    assert len(chunks_with_overlap) > 0
    
    # Check that overlap chunks have the correct metadata
    overlap_list_chunks = [c for c in chunks_with_overlap 
                          if c.metadata.get("node_type") == "list_container" and c.metadata.get("has_overlap")]
    
    for chunk in overlap_list_chunks:
        assert chunk.metadata["overlap_elements"] <= 2  # Should not exceed requested overlap
        assert chunk.metadata["overlap_elements"] > 0   # Should have some overlap


def test_overlap_prevents_infinite_loops():
    """Test that overlap doesn't cause infinite loops or excessive chunks."""
    chunker = DocChunker(chunk_size=50, num_overlapping_elements=3)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # This should complete in reasonable time without infinite loops
    chunks = chunker.process_document(str(test_file))
    
    # Should produce a reasonable number of chunks (not thousands)
    assert len(chunks) < 1000, f"Too many chunks produced: {len(chunks)}"
    assert len(chunks) > 0, "No chunks produced"
    
    # Each chunk should have valid token counts
    for chunk in chunks:
        assert chunk.metadata["num_tokens"] > 0
        assert chunk.text.strip(), "Empty chunk text"


def test_overlap_token_counting():
    """Test that token counting remains accurate with overlapping content."""
    chunker = DocChunker(chunk_size=80, num_overlapping_elements=1)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "sample_table.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    chunks = chunker.process_document(str(test_file))
    
    for chunk in chunks:
        # Token count should be reasonable and match the actual content
        estimated_tokens = len(chunk.text.split())  # Rough estimate
        actual_tokens = chunk.metadata["num_tokens"]
        
        # Should be in reasonable range (tokens are usually fewer than words)
        assert 0.5 * estimated_tokens <= actual_tokens <= 2.0 * estimated_tokens, \
            f"Token count {actual_tokens} seems unreasonable for text length {len(chunk.text)}"


def test_table_overlap_functionality():
    """Test overlapping specifically for table chunks."""
    # Use small chunk size to force table splitting
    chunker = DocChunker(chunk_size=60, num_overlapping_elements=1)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "sample_table.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    chunks = chunker.process_document(str(test_file))
    
    # Find table chunks
    table_chunks = [c for c in chunks if c.metadata.get("node_type") == "table_rows"]
    
    if len(table_chunks) > 1:
        # First table chunk should not have overlap
        assert table_chunks[0].metadata.get("has_overlap", False) == False
        
        # Subsequent table chunks should have overlap
        for chunk in table_chunks[1:]:
            assert chunk.metadata.get("has_overlap", False) == True
            assert chunk.metadata.get("overlap_elements", 0) > 0


def test_list_overlap_functionality():
    """Test overlapping specifically for list chunks."""
    # Use small chunk size to force list splitting
    chunker = DocChunker(chunk_size=40, num_overlapping_elements=2)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    chunks = chunker.process_document(str(test_file))
    
    # Find list chunks
    list_chunks = [c for c in chunks if c.metadata.get("node_type") == "list_container"]
    
    if len(list_chunks) > 1:
        # First list chunk should not have overlap
        assert list_chunks[0].metadata.get("has_overlap", False) == False
        
        # Check that overlapped chunks contain repeated content
        # (This is a more complex test that would need specific document structure)
        overlapped_chunks = [c for c in list_chunks if c.metadata.get("has_overlap", False)]
        
        for chunk in overlapped_chunks:
            assert chunk.metadata.get("overlap_elements", 0) <= 2  # Should not exceed requested
            assert chunk.metadata.get("overlap_elements", 0) > 0   # Should have some overlap


def test_overlap_with_edge_cases():
    """Test overlap functionality with edge cases."""
    # Test with overlap larger than possible elements
    chunker_big_overlap = DocChunker(chunk_size=200, num_overlapping_elements=100)
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "sample_table.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Should not crash even with very large overlap setting
    chunks = chunker_big_overlap.process_document(str(test_file))
    assert len(chunks) > 0
    
    # Overlap elements should never exceed the actual number of elements in chunk
    for chunk in chunks:
        if chunk.metadata.get("has_overlap", False):
            overlap_count = chunk.metadata.get("overlap_elements", 0)
            # This is a reasonable upper bound - overlap shouldn't be larger than total tokens / 10
            assert overlap_count <= chunk.metadata["num_tokens"] // 5


def test_document_chunker_direct():
    """Test DocumentChunker directly with overlap functionality."""
    from docchunker.processors.docx_parser import DocxParser
    
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    test_file = test_data_dir / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Test DocumentChunker directly
    parser = DocxParser()
    elements = parser.apply(str(test_file))
    
    chunker_no_overlap = DocumentChunker(chunk_size=50, num_overlapping_elements=0)
    chunks_no_overlap = chunker_no_overlap.apply(elements, str(test_file), "docx")
    
    chunker_with_overlap = DocumentChunker(chunk_size=50, num_overlapping_elements=1)
    chunks_with_overlap = chunker_with_overlap.apply(elements, str(test_file), "docx")
    
    # Both should produce valid chunks
    assert len(chunks_no_overlap) > 0
    assert len(chunks_with_overlap) > 0
    
    # Check metadata consistency
    for chunks in [chunks_no_overlap, chunks_with_overlap]:
        for chunk in chunks:
            assert hasattr(chunk, 'text')
            assert hasattr(chunk, 'metadata')
            assert chunk.metadata['num_tokens'] > 0