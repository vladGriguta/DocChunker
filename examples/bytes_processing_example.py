"""
Example demonstrating in-memory DOCX processing with DocChunker.

This example shows how to process DOCX documents from bytes or BytesIO objects,
which is useful for scenarios like:
- Processing files from web requests
- Working with documents stored in databases as BLOBs
- Processing files from cloud storage without writing to disk
- Working with dynamically generated documents
"""

import sys
from io import BytesIO
from pathlib import Path

# Add parent directory to sys.path to import docchunker
sys.path.append(str(Path(__file__).parent.parent))

from docchunker import DocChunker


def demonstrate_bytes_processing():
    """Demonstrate processing DOCX from bytes."""
    print("=== DocChunker In-Memory Processing Demo ===\n")
    
    # Initialize the chunker
    chunker = DocChunker(chunk_size=200)
    
    # Path to a sample DOCX file
    sample_file = Path(__file__).parent.parent / "data" / "unittests" / "sample_table.docx"
    
    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        print("Please ensure test data exists or use a different DOCX file.")
        return
    
    print(f"Using sample file: {sample_file}\n")
    
    # Method 1: Traditional file path processing (for comparison)
    print("1. Processing from file path (traditional method):")
    chunks_from_path = chunker.process_document(str(sample_file))
    print(f"   Generated {len(chunks_from_path)} chunks")
    
    # Method 2: Processing from bytes using the new method
    print("\n2. Processing from bytes (new method):")
    with open(sample_file, 'rb') as f:
        document_bytes = f.read()
    
    print(f"   Loaded {len(document_bytes)} bytes from file")
    chunks_from_bytes = chunker.process_document_bytes(document_bytes, "docx")
    print(f"   Generated {len(chunks_from_bytes)} chunks")
    
    # Method 3: Direct BytesIO processing through processor
    print("\n3. Processing from BytesIO object (direct processor access):")
    file_obj = BytesIO(document_bytes)
    docx_processor = chunker.processors["docx"]
    chunks_from_bytesio = docx_processor.process(file_obj)
    print(f"   Generated {len(chunks_from_bytesio)} chunks")
    
    # Verify all methods produce identical results
    print("\n=== Verification ===")
    
    methods_match = (
        len(chunks_from_path) == len(chunks_from_bytes) == len(chunks_from_bytesio)
    )
    
    if methods_match:
        content_match = all(
            chunks_from_path[i].text == chunks_from_bytes[i].text == chunks_from_bytesio[i].text
            for i in range(len(chunks_from_path))
        )
        
        if content_match:
            print("✓ All three methods produced identical results!")
        else:
            print("⚠ Methods produced same number of chunks but content differs")
    else:
        print("⚠ Methods produced different numbers of chunks")
    
    # Display sample content
    print(f"\n=== Sample Content ===")
    if chunks_from_bytes:
        print("First chunk from bytes processing:")
        print(f"   Text: {chunks_from_bytes[0].text[:100]}...")
        print(f"   Metadata: {chunks_from_bytes[0].metadata}")


def demonstrate_error_handling():
    """Demonstrate error handling with invalid inputs."""
    print("\n=== Error Handling Demo ===")
    
    chunker = DocChunker()
    
    # Test invalid format
    try:
        chunker.process_document_bytes(b"fake content", "invalid")
    except ValueError as e:
        print(f"✓ Correctly caught error for invalid format: {e}")
    
    # Test invalid DOCX content
    try:
        chunker.process_document_bytes(b"not a docx file", "docx")
    except Exception as e:
        print(f"✓ Correctly caught error for invalid DOCX content: {type(e).__name__}")


def main():
    """Main function demonstrating the new functionality."""
    try:
        demonstrate_bytes_processing()
        demonstrate_error_handling()
        
        print("\n=== Use Cases ===")
        print("The bytes processing functionality enables:")
        print("• Processing documents from web uploads without saving to disk")
        print("• Working with documents stored in databases as BLOBs")  
        print("• Processing files from cloud storage APIs")
        print("• Handling dynamically generated documents")
        print("• Memory-efficient processing in containerized environments")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()