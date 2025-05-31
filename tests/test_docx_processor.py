import pytest
import yaml
from pathlib import Path
from docchunker import DocChunker
from docchunker.models.chunk import Chunk


class TestYamlDriven:
    """Generic test class that uses YAML configurations."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Get the test data directory."""
        return Path(__file__).parent.parent / "data" / "unittests"
    
    @pytest.fixture
    def chunker(self):
        """Create DocChunker instance."""
        return DocChunker(
            chunk_size=1000,
            chunk_overlap=200,
            preserve_structure=True,
            handle_lists=True,
            handle_tables=True
        )
    
    def get_test_configs(self, test_data_dir):
        """Find all YAML test configurations."""
        yaml_files = list(test_data_dir.glob("*.yaml"))
        configs = []
        
        for yaml_file in yaml_files:
            with open(yaml_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check if corresponding docx exists
            docx_file = test_data_dir / config['document']
            if docx_file.exists():
                configs.append((yaml_file.stem, config, docx_file))
            else:
                print(f"Warning: {config['document']} not found for {yaml_file}")
        
        return configs
    
    def test_all_yaml_configs(self, test_data_dir, chunker):
        """Test all YAML configurations found in test data directory."""
        configs = self.get_test_configs(test_data_dir)
        
        if not configs:
            pytest.skip("No valid YAML/DOCX pairs found in test data directory")
        
        for test_name, config, docx_file in configs:
            print(f"\n--- Testing {test_name} ---")
            self._test_single_config(config, docx_file, chunker)
    
    def _test_single_config(self, config, docx_file, chunker):
        """Test a single YAML configuration."""
        # Process document
        chunks = chunker.process_document(str(docx_file))
        assert len(chunks) > 0, f"No chunks generated for {docx_file}"
        
        # Run global checks
        if 'global_checks' in config:
            self._run_global_checks(chunks, config['global_checks'])
        
        # Run specific test cases
        if 'test_cases' in config:
            for test_case in config['test_cases']:
                self._run_test_case(chunks, test_case)
    
    def _run_global_checks(self, chunks, global_checks):
        """Run global document checks."""
        # Check minimum chunks
        if 'min_chunks' in global_checks:
            min_chunks = global_checks['min_chunks']
            assert len(chunks) >= min_chunks, \
                f"Expected at least {min_chunks} chunks, got {len(chunks)}"
        
        print(f"✓ Global checks passed for {len(chunks)} chunks")

    def _run_test_case(self, chunks, test_case):
        """Run a specific test case."""
        search_text = test_case['search_text']
        test_name = test_case['name']
        
        # Find chunks containing the search text
        matching_chunks = [c for c in chunks if search_text in c.text]
        
        assert len(matching_chunks) > 0, \
            f"Test '{test_name}': No chunks found containing '{search_text}'"
        
        # For each matching chunk, run the checks
        for chunk in matching_chunks:
            # Check expected context in chunk
            if 'expected_in_chunk' in test_case:
                for expected_text in test_case['expected_in_chunk']:
                    assert expected_text in chunk.text, \
                        f"Test '{test_name}': Expected '{expected_text}' in same chunk as '{search_text}'"
            
            # Check expected metadata
            if 'expected_metadata' in test_case:
                for key, expected_value in test_case['expected_metadata'].items():
                    actual_value = chunk.metadata.get(key)
                    assert actual_value == expected_value, \
                        f"Test '{test_name}': Expected {key}='{expected_value}', got '{actual_value}'"
        
        print(f"✓ Test case '{test_name}' passed ({len(matching_chunks)} matching chunks)")
