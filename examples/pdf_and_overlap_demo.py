"""
PDF Processing and Overlap Functionality Demo for DocChunker.

This example demonstrates:
1. PDF document processing with structure detection
2. Element overlap functionality for better context preservation
3. Comparison between different overlap settings
4. Processing from different input sources (file path, bytes, BytesIO)
"""

import sys
from pathlib import Path
from io import BytesIO

# Add parent directory to sys.path to import docchunker
sys.path.append(str(Path(__file__).parent.parent))

from docchunker import DocChunker


def demonstrate_pdf_processing():
    """Demonstrate PDF processing capabilities."""
    print("=== PDF Processing Demo ===")
    
    # Find test PDF files
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    pdf_files = list(test_data_dir.glob("*.pdf")) if test_data_dir.exists() else []
    
    if not pdf_files:
        print("No PDF test files found. Please add some PDF files to data/unittests/")
        return
    
    test_file = pdf_files[0]
    print(f"Processing: {test_file.name}")
    
    # Standard PDF processing
    chunker = DocChunker(chunk_size=200)
    chunks = chunker.process_document(str(test_file))
    
    print(f"\nGenerated {len(chunks)} chunks from PDF")
    print("Document structure detected:")
    
    # Analyze detected structure
    node_types = {}
    for chunk in chunks:
        node_type = chunk.metadata.get("node_type", "unknown")
        source_type = chunk.metadata.get("source_type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Verify all chunks are marked as PDF
        assert source_type == "pdf", f"Expected PDF source type, got {source_type}"
    
    for node_type, count in sorted(node_types.items()):
        print(f"  {node_type}: {count} chunks")
    
    return test_file, chunks


def demonstrate_overlap_functionality(test_file: Path):
    """Demonstrate overlap functionality with different settings."""
    print(f"\n=== Overlap Functionality Demo ===")
    print(f"Using file: {test_file.name}")
    
    # Test different overlap configurations
    configurations = [
        (0, "No Overlap"),
        (1, "Light Overlap (1 element)"), 
        (2, "Medium Overlap (2 elements)"),
        (3, "Heavy Overlap (3 elements)")
    ]
    
    results = {}
    
    for num_overlap, description in configurations:
        print(f"\n--- {description} ---")
        
        chunker = DocChunker(
            chunk_size=100,  # Smaller chunk size to force splitting
            num_overlapping_elements=num_overlap
        )
        
        chunks = chunker.process_document(str(test_file))
        
        # Count overlapped chunks
        overlapped_chunks = [c for c in chunks if c.metadata.get("has_overlap", False)]
        total_overlap_elements = sum(c.metadata.get("overlap_elements", 0) for c in overlapped_chunks)
        
        print(f"Total chunks: {len(chunks)}")
        print(f"Overlapped chunks: {len(overlapped_chunks)}")
        print(f"Total overlapped elements: {total_overlap_elements}")
        
        # Show example of overlapped content
        if overlapped_chunks:
            example_chunk = overlapped_chunks[0]
            print(f"Example overlapped chunk metadata:")
            print(f"  has_overlap: {example_chunk.metadata.get('has_overlap')}")
            print(f"  overlap_elements: {example_chunk.metadata.get('overlap_elements')}")
            print(f"  node_type: {example_chunk.metadata.get('node_type')}")
        
        results[description] = {
            'total_chunks': len(chunks),
            'overlapped_chunks': len(overlapped_chunks),
            'total_chars': sum(len(c.text) for c in chunks)
        }
    
    # Summary comparison
    print(f"\n--- Overlap Configuration Comparison ---")
    print(f"{'Configuration':<25} | {'Chunks':<7} | {'Overlap':<8} | {'Total Chars'}")
    print("-" * 65)
    for config, data in results.items():
        print(f"{config:<25} | {data['total_chunks']:<7} | {data['overlapped_chunks']:<8} | {data['total_chars']}")


def demonstrate_input_methods(test_file: Path):
    """Demonstrate different input methods for processing."""
    print(f"\n=== Input Method Demo ===")
    
    chunker = DocChunker(chunk_size=200, num_overlapping_elements=1)
    
    # Method 1: File path
    print("1. Processing from file path...")
    chunks_path = chunker.process_document(str(test_file))
    print(f"   Chunks from file path: {len(chunks_path)}")
    
    # Method 2: Bytes
    print("2. Processing from bytes...")
    with open(test_file, 'rb') as f:
        document_bytes = f.read()
    chunks_bytes = chunker.process_document_bytes(document_bytes, "pdf")
    print(f"   Chunks from bytes: {len(chunks_bytes)}")
    
    # Method 3: BytesIO (direct processor access)
    print("3. Processing from BytesIO...")
    file_obj = BytesIO(document_bytes)
    pdf_processor = chunker.processors["pdf"]
    chunks_bytesio = pdf_processor.process(file_obj)
    print(f"   Chunks from BytesIO: {len(chunks_bytesio)}")
    
    # Verify consistency
    print(f"\nConsistency check:")
    print(f"   All methods produce same chunk count: {len(chunks_path) == len(chunks_bytes) == len(chunks_bytesio)}")
    
    # Compare first chunk text (should be identical)
    if chunks_path and chunks_bytes and chunks_bytesio:
        texts_match = (chunks_path[0].text == chunks_bytes[0].text == chunks_bytesio[0].text)
        print(f"   First chunk text identical: {texts_match}")


def demonstrate_context_preservation():
    """Show how overlap helps preserve context."""
    print(f"\n=== Context Preservation Demo ===")
    
    # Find a file with lists or tables for better demonstration
    test_data_dir = Path(__file__).parent.parent / "data" / "unittests"
    
    # Look for files likely to have lists or tables
    test_files = []
    if test_data_dir.exists():
        for pattern in ["*list*.pdf", "*table*.pdf", "*.pdf"]:
            test_files.extend(test_data_dir.glob(pattern))
    
    if not test_files:
        print("No suitable test files found for context preservation demo")
        return
    
    test_file = test_files[0]
    
    # Compare no overlap vs overlap
    print(f"Comparing context preservation using: {test_file.name}")
    
    # No overlap
    chunker_no_overlap = DocChunker(chunk_size=80, num_overlapping_elements=0) 
    chunks_no_overlap = chunker_no_overlap.process_document(str(test_file))
    
    # With overlap
    chunker_with_overlap = DocChunker(chunk_size=80, num_overlapping_elements=2)
    chunks_with_overlap = chunker_with_overlap.process_document(str(test_file))
    
    print(f"\nNo overlap: {len(chunks_no_overlap)} chunks")
    print(f"With overlap: {len(chunks_with_overlap)} chunks")
    
    # Find list or table chunks for comparison
    interesting_chunks_no_overlap = [c for c in chunks_no_overlap 
                                   if c.metadata.get("node_type") in ["list_container", "table_rows"]]
    interesting_chunks_with_overlap = [c for c in chunks_with_overlap 
                                     if c.metadata.get("node_type") in ["list_container", "table_rows"]]
    
    if interesting_chunks_with_overlap:
        print(f"\nFound {len(interesting_chunks_with_overlap)} list/table chunks with overlap")
        
        # Show overlap metadata for interesting chunks
        overlapped = [c for c in interesting_chunks_with_overlap if c.metadata.get("has_overlap")]
        if overlapped:
            print(f"Overlapped list/table chunks: {len(overlapped)}")
            example = overlapped[0]
            print(f"Example overlap: {example.metadata.get('overlap_elements')} elements")
            print(f"Chunk preview: {example.text[:100]}...")


def main():
    """Main demonstration function."""
    print("DocChunker PDF and Overlap Functionality Demo")
    print("=" * 50)
    
    # 1. Basic PDF processing
    test_file, _ = demonstrate_pdf_processing()
    
    if not test_file:
        return
    
    # 2. Overlap functionality
    demonstrate_overlap_functionality(test_file)
    
    # 3. Different input methods
    demonstrate_input_methods(test_file)
    
    # 4. Context preservation benefits
    demonstrate_context_preservation()
    
    print(f"\n{'='*50}")
    print("Demo completed successfully!")
    print("\nKey takeaways:")
    print("• PDF processing works identically to DOCX processing")
    print("• Overlap helps preserve context between chunks")
    print("• Different input methods (file/bytes/BytesIO) produce consistent results")
    print("• Overlap is especially useful for lists and tables")
    print("• Configure overlap based on your use case (0-3 elements recommended)")


if __name__ == "__main__":
    main()