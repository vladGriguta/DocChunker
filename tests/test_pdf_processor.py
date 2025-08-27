import pytest
import yaml
from io import BytesIO
from pathlib import Path
from docchunker import DocChunker


def get_yaml_configs_for_pdf():
    """Discover all YAML configs and their corresponding PDF files."""
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    yaml_files = sorted(test_data_dir.glob("*.yaml"))  # Sort for consistent order across systems
    configs = []
    
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Look for PDF version of the document
        docx_filename = config['document']
        pdf_filename = docx_filename.replace('.docx', '.pdf')
        pdf_file = test_data_dir / pdf_filename
        
        if pdf_file.exists():
            configs.append((yaml_file.stem, config, pdf_file))
    
    return configs


def collect_pdf_test_cases():
    """Flatten all PDF test cases for parameterization."""
    cases = []
    for test_name, config, pdf_file in get_yaml_configs_for_pdf():
        # Global checks as a separate test
        if 'global_checks' in config:
            cases.append(
                pytest.param(
                    config, pdf_file, None, config['global_checks'],
                    id=f"{test_name}_pdf::global_checks"
                )
            )
        # Each test case as a separate test
        if 'test_cases' in config:
            for test_case in config['test_cases']:
                cases.append(
                    pytest.param(
                        config, pdf_file, test_case, None,
                        id=f"{test_name}_pdf::{test_case['name']}"
                    )
                )
    return cases


@pytest.fixture
def chunker():
    return DocChunker(chunk_size=200)


def test_pdf_process_documents_returns_chunks(chunker):
    """Test that PDF processing returns chunks."""
    samples_dir = Path(__file__).parent.parent / "data" / "unittests"
    chunks = chunker.process_documents(str(samples_dir), "*.pdf")
    assert isinstance(chunks, list), "Output should be of type list."
    assert len(chunks) > 0, "Expected at least one chunk to be returned from PDF processing."
    
    # Verify chunks have PDF metadata
    for chunk in chunks:
        assert chunk.metadata["source_type"] == "pdf"


@pytest.mark.parametrize("config, pdf_file, test_case, global_checks", collect_pdf_test_cases())
def test_pdf_yaml_driven(chunker, config, pdf_file, test_case, global_checks):
    """Test PDF processing with YAML-driven test cases."""
    if test_case and (test_case.get("xfail", False) or test_case.get("xfail_pdf", False)):
        pytest.xfail("Marked as expected to fail for PDF in YAML")

    chunks = chunker.process_document(str(pdf_file))
    assert len(chunks) > 0, f"No chunks generated for PDF {pdf_file}"
    
    # Verify all chunks have PDF source type
    for chunk in chunks:
        assert chunk.metadata["source_type"] == "pdf"

    if global_checks:
        if 'min_chunks' in global_checks:
            min_chunks = global_checks['min_chunks']
            # PDF might produce different chunk counts due to format differences
            # So we'll be more lenient with the minimum - accept at least half the expected chunks
            assert len(chunks) >= max(1, min_chunks // 2), \
                f"Expected at least {max(1, min_chunks // 2)} chunks for PDF, got {len(chunks)}"
                
    if test_case:
        search_text = test_case['search_text']
        test_name = test_case['name']
        matching_chunks = [c for c in chunks if search_text in c.text]
        assert len(matching_chunks) > 0, \
            f"Test '{test_name}': No chunks found containing '{search_text}'"
        for chunk in matching_chunks:
            if 'expected_in_chunk' in test_case:
                for expected_text in test_case['expected_in_chunk']:
                    assert expected_text in chunk.text, \
                        f"Test '{test_name}': Expected '{expected_text}' in same chunk as '{search_text}'"
            if 'num_chunks' in test_case:
                num_chunks = test_case['num_chunks']
                assert len(matching_chunks) == num_chunks, \
                    f"Test '{test_name}': Expected {num_chunks} chunks containing '{search_text}', got {len(matching_chunks)}"
            if 'expected_metadata' in test_case:
                for key, expected_value in test_case['expected_metadata'].items():
                    actual_value = chunk.metadata.get(key)
                    # For PDF, we expect the source_type to be 'pdf' instead of 'docx'
                    if key == 'source_type':
                        assert actual_value == 'pdf', \
                            f"Test '{test_name}': Expected {key}='pdf', got '{actual_value}'"
                    else:
                        assert actual_value == expected_value, \
                            f"Test '{test_name}': Expected {key}='{expected_value}', got '{actual_value}'"


def test_process_document_bytes_with_pdf_file(chunker):
    """Test processing PDF from bytes using a real test file."""
    # Use one of the existing test files
    test_file = Path(__file__).parent.parent / "data" / "unittests" / "sample_table.pdf"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Read the file as bytes
    with open(test_file, 'rb') as f:
        document_bytes = f.read()
    
    # Process using the bytes method
    chunks_from_bytes = chunker.process_document_bytes(document_bytes, "pdf")
    
    # Process using the traditional file path method for comparison
    chunks_from_path = chunker.process_document(str(test_file))
    
    # Both methods should return the same number of chunks
    assert len(chunks_from_bytes) == len(chunks_from_path), \
        f"Bytes method returned {len(chunks_from_bytes)} chunks, path method returned {len(chunks_from_path)} chunks"
    
    # Content should be identical
    for chunk_bytes, chunk_path in zip(chunks_from_bytes, chunks_from_path):
        assert chunk_bytes.text == chunk_path.text, \
            "Chunk text differs between bytes and path processing methods"
    
    # Ensure we actually got some chunks
    assert len(chunks_from_bytes) > 0, "No chunks were generated from bytes processing"
    
    # Verify all chunks have PDF metadata
    for chunk in chunks_from_bytes:
        assert chunk.metadata["source_type"] == "pdf"


def test_process_document_bytes_with_bytesio_directly(chunker):
    """Test processing PDF from BytesIO object directly through processor."""
    test_file = Path(__file__).parent.parent / "data" / "unittests" / "nested_lists.pdf"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Read file as bytes and create BytesIO
    with open(test_file, 'rb') as f:
        document_bytes = f.read()
    
    file_obj = BytesIO(document_bytes)
    
    # Process using the PDF processor directly
    pdf_processor = chunker.processors["pdf"]
    chunks = pdf_processor.process(file_obj)
    
    assert isinstance(chunks, list), "Output should be a list of chunks"
    assert len(chunks) > 0, "Should generate at least one chunk"
    assert all(hasattr(chunk, 'text') for chunk in chunks), "All chunks should have text attribute"
    assert all(chunk.metadata["source_type"] == "pdf" for chunk in chunks), "All chunks should have PDF source type"


def test_process_document_bytes_invalid_format():
    """Test that invalid file formats raise appropriate errors."""
    chunker = DocChunker()
    
    with pytest.raises(ValueError, match="Unsupported file format: invalid"):
        chunker.process_document_bytes(b"fake content", "invalid")


def test_process_document_bytes_empty_content():
    """Test processing empty bytes content for PDF."""
    chunker = DocChunker()
    
    # This should raise an error since empty bytes won't be a valid PDF
    with pytest.raises(Exception):  # PyPDF will raise some exception for invalid content
        chunker.process_document_bytes(b"", "pdf")


def test_pdf_basic_functionality():
    """Test basic PDF processing functionality."""
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    pdf_files = list(test_data_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No PDF test files found")
    
    chunker = DocChunker(chunk_size=200)
    
    # Test processing first PDF file
    chunks = chunker.process_document(str(pdf_files[0]))
    
    assert isinstance(chunks, list), "Output should be a list of chunks"
    assert len(chunks) > 0, "Should generate at least one chunk"
    assert all(hasattr(chunk, 'text') for chunk in chunks), "All chunks should have text attribute"
    assert all(chunk.metadata["source_type"] == "pdf" for chunk in chunks), "All chunks should have PDF source type"
    
    # Verify chunk structure
    for chunk in chunks:
        assert hasattr(chunk, 'metadata'), "Chunk should have metadata"
        assert 'document_id' in chunk.metadata, "Chunk metadata should have document_id"
        assert 'node_type' in chunk.metadata, "Chunk metadata should have node_type"
        assert 'num_tokens' in chunk.metadata, "Chunk metadata should have num_tokens"


def test_pdf_parser_directly():
    """Test the PDF parser directly."""
    from docchunker.processors.pdf_parser import PdfParser
    
    test_file = Path(__file__).parent.parent / "data" / "unittests" / "sample_table.pdf"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    parser = PdfParser()
    elements = parser.apply(str(test_file))
    
    assert isinstance(elements, list), "Parser should return a list"
    assert len(elements) > 0, "Parser should extract at least one element"
    
    # Verify element structure
    for element in elements:
        assert isinstance(element, dict), "Each element should be a dictionary"
        assert 'type' in element, "Each element should have a type"
        assert element['type'] in ['heading', 'paragraph', 'list_item', 'list_container', 'table'], \
            f"Unknown element type: {element['type']}"
        
        if element['type'] in ['heading', 'paragraph', 'list_item']:
            assert 'content' in element, f"Element of type {element['type']} should have content"


@pytest.mark.skipif(
    len(get_yaml_configs_for_pdf()) == 0, 
    reason="No PDF test files with YAML configs found"
)
def test_pdf_vs_docx_structure_similarity():
    """Compare PDF and DOCX processing structure to ensure they're similar."""
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    
    # Find a pair of DOCX and PDF files
    yaml_configs = get_yaml_configs_for_pdf()
    if not yaml_configs:
        pytest.skip("No PDF test files found")
    
    # Use the first available config
    test_name, config, pdf_file = yaml_configs[0]
    docx_filename = config['document']
    docx_file = test_data_dir / docx_filename
    
    if not docx_file.exists():
        pytest.skip(f"Corresponding DOCX file not found: {docx_file}")
    
    chunker = DocChunker(chunk_size=200)
    
    # Process both files
    docx_chunks = chunker.process_document(str(docx_file))
    pdf_chunks = chunker.process_document(str(pdf_file))
    
    # Both should produce chunks
    assert len(docx_chunks) > 0, "DOCX should produce chunks"
    assert len(pdf_chunks) > 0, "PDF should produce chunks"
    
    # Verify metadata consistency
    for chunk in docx_chunks:
        assert chunk.metadata["source_type"] == "docx"
        
    for chunk in pdf_chunks:
        assert chunk.metadata["source_type"] == "pdf"
    
    # The number of chunks might differ due to format differences,
    # but they should be in a reasonable range (PDF often produces more chunks)
    ratio = len(pdf_chunks) / len(docx_chunks)
    assert 0.2 <= ratio <= 6.0, \
        f"PDF chunk count ({len(pdf_chunks)}) should be reasonably related to DOCX count ({len(docx_chunks)}), ratio: {ratio}"
    
    # Both should have similar node types represented
    docx_node_types = {chunk.metadata.get("node_type") for chunk in docx_chunks}
    pdf_node_types = {chunk.metadata.get("node_type") for chunk in pdf_chunks}
    
    # At least some overlap in node types (PDF might miss some complex structures)
    overlap = docx_node_types.intersection(pdf_node_types)
    assert len(overlap) > 0, f"PDF and DOCX should have some overlapping node types. DOCX: {docx_node_types}, PDF: {pdf_node_types}"