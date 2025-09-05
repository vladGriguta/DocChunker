"""
Basic usage example for the DocChunker library.

This example demonstrates how to process both DOCX and PDF documents with different
configurations including overlap settings.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to sys.path to import docchunker
sys.path.append(str(Path(__file__).parent.parent))

from docchunker import DocChunker
from docchunker.models.chunk import Chunk


def process_document_with_config(file_path: Path, chunker: DocChunker, config_name: str) -> list[Chunk]:
    """Process a document and display statistics."""
    print(f"\n--- Processing with {config_name} ---")
    print(f"Document: {file_path.name}")
    print(f"Settings: chunk_size={chunker.chunk_size} chars, overlap={chunker.processors['docx'].chunker.num_overlapping_elements}")
    
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return []
    
    # Process the document
    chunks = chunker.process_document(str(file_path))
    print(f"Generated {len(chunks)} chunks")
    
    # Analyze chunk types and overlap
    chunk_types = {}
    overlap_count = 0
    
    for chunk in chunks:
        node_type = chunk.metadata.get("node_type", "unknown")
        chunk_types[node_type] = chunk_types.get(node_type, 0) + 1
        
        if chunk.metadata.get("has_overlap", False):
            overlap_count += 1
    
    print(f"Chunks with overlap: {overlap_count}")
    print("Node type distribution:")
    for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {chunk_type}: {count}")
    
    return chunks


def main():
    # Set up paths
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    data_dir = root_dir / "data"
    samples_dir = data_dir / "samples"
    unittest_dir = data_dir / "unittests"
    output_dir = data_dir / "output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("=== DocChunker Advanced Usage Example ===")
    print("\nThis example demonstrates:")
    print("1. Processing both DOCX and PDF documents")
    print("2. Using different overlap configurations")
    print("3. Comparing chunking strategies")
    
    # Test documents (try multiple sources)
    test_documents = []
    
    # Try samples directory first
    for ext in ['docx', 'pdf']:
        sample_file = samples_dir / f"complex_document.{ext}"
        if sample_file.exists():
            test_documents.append(sample_file)
    
    # Try unittest data directory  
    if unittest_dir.exists():
        for ext in ['docx', 'pdf']:
            for test_file in unittest_dir.glob(f"*.{ext}"):
                if test_file not in test_documents:
                    test_documents.append(test_file)
                    break  # Just take the first one of each type
    
    if not test_documents:
        print("No test documents found. Please add some .docx or .pdf files to:")
        print(f"  {samples_dir}")
        print(f"  {unittest_dir}")
        return
    
    print(f"\nFound {len(test_documents)} test documents:")
    for doc in test_documents:
        print(f"  {doc}")
    
    # Configuration 1: Standard chunking (no overlap)
    chunker_standard = DocChunker(chunk_size=750, num_overlapping_elements=0)
    
    # Configuration 2: Small overlap for context
    chunker_overlap_small = DocChunker(chunk_size=750, num_overlapping_elements=1)
    
    # Configuration 3: Larger overlap for high-context applications
    chunker_overlap_large = DocChunker(chunk_size=1000, num_overlapping_elements=3)
    
    configurations = [
        (chunker_standard, "Standard (no overlap)"),
        (chunker_overlap_small, "Small overlap (1 element)"), 
        (chunker_overlap_large, "Large overlap (3 elements)")
    ]
    
    all_results = {}
    
    # Process each document with each configuration
    for doc_path in test_documents[:2]:  # Limit to first 2 documents for demo
        print(f"\n{'='*60}")
        print(f"DOCUMENT: {doc_path.name}")
        print(f"{'='*60}")
        
        doc_results = {}
        
        for chunker, config_name in configurations:
            chunks = process_document_with_config(doc_path, chunker, config_name)
            doc_results[config_name] = chunks
            
            # Save chunks for this configuration
            if chunks:
                # Include file extension in output name to distinguish between DOCX and PDF
                file_type = doc_path.suffix.lower().replace('.', '')
                config_slug = config_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                output_file = output_dir / f"{doc_path.stem}_{file_type}_{config_slug}_chunks.json"
                save_chunks_to_json(chunks, output_file)
                print(f"Saved to: {output_file.name}")
        
        all_results[doc_path.name] = doc_results
    
    # Comparison summary
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    
    for doc_name, doc_results in all_results.items():
        print(f"\n{doc_name}:")
        for config_name, chunks in doc_results.items():
            if chunks:
                total_chars = sum(len(chunk.text) for chunk in chunks)
                overlap_chunks = sum(1 for chunk in chunks if chunk.metadata.get("has_overlap", False))
                print(f"  {config_name:25} | {len(chunks):3} chunks | {overlap_chunks:2} overlapped | {total_chars:5} chars")
    
    print(f"\nAll output files saved to: {output_dir}")


def save_chunks_to_json(chunks: list[Chunk], output_file: Path):
    """Save chunks to JSON with proper serialization."""
    chunks_data = []
    for i, chunk in enumerate(chunks):
        chunk_data = {
            "chunk_id": i,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "text_length": len(chunk.text)
        }
        chunks_data.append(chunk_data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()