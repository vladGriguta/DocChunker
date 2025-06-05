import pytest
import yaml
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
    if test_case and test_case.get("xfail", False):
        pytest.xfail("Marked as expected to fail in YAML")

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
            if 'expected_metadata' in test_case:
                for key, expected_value in test_case['expected_metadata'].items():
                    actual_value = chunk.metadata.get(key)
                    assert actual_value == expected_value, \
                        f"Test '{test_name}': Expected {key}='{expected_value}', got '{actual_value}'"