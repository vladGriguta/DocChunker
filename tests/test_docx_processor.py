import pytest
import yaml
from io import BytesIO
from pathlib import Path
from docchunker import DocChunker

def get_yaml_configs():
    """Discover all YAML configs and their corresponding docx files."""
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    yaml_files = list(test_data_dir.glob("*.yaml"))
    configs = []
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
        docx_file = test_data_dir / config['document']
        if docx_file.exists():
            configs.append((yaml_file.stem, config, docx_file))
    return configs

def collect_test_cases():
    """Flatten all test cases for parameterization."""
    cases = []
    for test_name, config, docx_file in get_yaml_configs():
        # Global checks as a separate test
        if 'global_checks' in config:
            cases.append(
                pytest.param(
                    config, docx_file, None, config['global_checks'],
                    id=f"{test_name}::global_checks"
                )
            )
        # Each test case as a separate test
        if 'test_cases' in config:
            for test_case in config['test_cases']:
                cases.append(
                    pytest.param(
                        config, docx_file, test_case, None,
                        id=f"{test_name}::{test_case['name']}"
                    )
                )
    return cases

@pytest.fixture
def chunker():
    return DocChunker(chunk_size=200)

def test_process_documents_returns_chunks(chunker):
    samples_dir = Path(__file__).parent.parent / "data" / "unittests"
    chunks = chunker.process_documents(str(samples_dir), "*.docx")
    assert isinstance(chunks, list), "Output should be of type list."
    assert len(chunks) > 0, "Expected at least one chunk to be returned from process_documents."

@pytest.mark.parametrize("config, docx_file, test_case, global_checks", collect_test_cases())
def test_yaml_driven(chunker, config, docx_file, test_case, global_checks):
    if test_case and (test_case.get("xfail", False) or test_case.get("xfail_docx", False)):
        pytest.xfail("Marked as expected to fail for DOCX in YAML")

    chunks = chunker.process_document(str(docx_file))
    assert len(chunks) > 0, f"No chunks generated for {docx_file}"

    if global_checks:
        if 'min_chunks' in global_checks:
            min_chunks = global_checks['min_chunks']
            assert len(chunks) >= min_chunks, \
                f"Expected at least {min_chunks} chunks, got {len(chunks)}"
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
                    assert actual_value == expected_value, \
                        f"Test '{test_name}': Expected {key}='{expected_value}', got '{actual_value}'"

def test_process_document_bytes_with_sample_file(chunker):
    """Test processing DOCX from bytes using a real test file."""
    # Use one of the existing test files
    test_file = Path(__file__).parent.parent / "data" / "unittests" / "sample_table.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Read the file as bytes
    with open(test_file, 'rb') as f:
        document_bytes = f.read()
    
    # Process using the new bytes method
    chunks_from_bytes = chunker.process_document_bytes(document_bytes, "docx")
    
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

def test_process_document_bytes_with_bytesio_directly(chunker):
    """Test processing DOCX from BytesIO object directly through processor."""
    test_file = Path(__file__).parent.parent / "data" / "unittests" / "nested_lists.docx"
    
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")
    
    # Read file as bytes and create BytesIO
    with open(test_file, 'rb') as f:
        document_bytes = f.read()
    
    file_obj = BytesIO(document_bytes)
    
    # Process using the DOCX processor directly
    docx_processor = chunker.processors["docx"]
    chunks = docx_processor.process(file_obj)
    
    assert isinstance(chunks, list), "Output should be a list of chunks"
    assert len(chunks) > 0, "Should generate at least one chunk"
    assert all(hasattr(chunk, 'text') for chunk in chunks), "All chunks should have text attribute"

def test_process_document_bytes_invalid_format():
    """Test that invalid file formats raise appropriate errors."""
    chunker = DocChunker()
    
    with pytest.raises(ValueError, match="Unsupported file format: invalid"):
        chunker.process_document_bytes(b"fake content", "invalid")

def test_process_document_bytes_empty_content():
    """Test processing empty bytes content."""
    chunker = DocChunker()
    
    # This should raise an error since empty bytes won't be a valid DOCX
    with pytest.raises(Exception):  # python-docx will raise some exception for invalid content
        chunker.process_document_bytes(b"", "docx")