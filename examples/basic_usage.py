"""
Basic usage example for the DocChunker library.

This example demonstrates how to process a complex document and explore the resulting chunks.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to sys.path to import docchunker
sys.path.append(str(Path(__file__).parent.parent))

from docchunker import DocChunker
from docchunker.models.chunk import Chunk


def main():
    # Set up paths
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    data_dir = root_dir / "data"
    samples_dir = data_dir / "samples"
    output_dir = data_dir / "output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the chunker with custom settings
    chunker = DocChunker(chunk_size=200)
    
    print("DocChunker initialized with settings:")
    print(f"  Chunk size: {chunker.chunk_size}")
    
    # Process a sample document
    file_path = samples_dir / "complex_document.docx"
    print(f"\nProcessing document: {file_path}")
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        print("Please make sure to save the complex document as 'complex_document.docx' in the data/samples directory.")
        return
    
    # Process the document
    chunks = chunker.process_document(str(file_path))
    
    print(f"\nDocument processed successfully. Generated {len(chunks)} chunks.")
    
    # Analyze chunk types
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk.metadata.get("type", "unknown")
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print("\nChunk type distribution:")
    for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {chunk_type}: {count}")
    
    # Save all chunks to JSON
    output_file = output_dir / "chunks.json"
    chunker.export_chunks_to_json(chunks, output_file)
    
    print(f"\nAll chunks saved to: {output_file}")
    
    # Generate statistics
    total_chars = sum(len(chunk.text) for chunk in chunks)
    avg_chunk_size = total_chars / len(chunks) if chunks else 0
    
    print("\nChunking statistics:")
    print(f"  Total characters: {total_chars}")
    print(f"  Average chunk size: {avg_chunk_size:.1f} characters")
    print(f"  Smallest chunk: {min(len(chunk.text) for chunk in chunks) if chunks else 0} characters")
    print(f"  Largest chunk: {max(len(chunk.text) for chunk in chunks) if chunks else 0} characters")


if __name__ == "__main__":
    main()