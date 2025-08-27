# DocChunker

A specialized document chunking library designed to handle complex document structures in DOCX and PDF files. DocChunker intelligently processes structured documents containing tables, nested lists, images, and other complex elements to create semantically meaningful chunks that preserve context.

DocChunker supports flexible input methods - process documents from file paths, raw bytes, or file-like objects, making it ideal for web applications, database integration, and cloud-based document processing pipelines.

## Key Features

*   **In-Memory Processing**: Process documents from bytes, BytesIO objects, or file paths - perfect for web uploads, databases, and cloud storage.
*   **Multi-Format Support**: Full support for DOCX and PDF documents with intelligent structure detection.
*   **Advanced Document Parsing**: Handles complex elements like nested lists, tables with merged cells, headings, and paragraphs.
*   **Contextual Chunking**: Preserves document hierarchy (headings, etc.) within chunks for better semantic understanding.
*   **Overlap Control**: Configure element-based overlap between chunks to maintain context continuity.
*   **Configurable Strategy**: Tune chunk size (tokens) and overlap parameters for optimal performance.
*   **Semantic Cohesion**: Aims to keep related content (list items, table rows) together.
*   **RAG-Optimized**: Produces chunks ideal for effective information retrieval.

## Installation

```bash
pip install docchunker
```

DocChunker requires Python 3.9+ and supports both DOCX and PDF processing out of the box.

## Quick Start

### Basic Usage

```python
from docchunker import DocChunker

# Initialize the chunker with desired settings
chunker = DocChunker(chunk_size=200)

# Process DOCX from file path
chunks = chunker.process_document("document.docx")

# Process PDF from file path  
chunks = chunker.process_document("document.pdf")

# Process from bytes (web uploads, database, etc.)
with open("document.docx", "rb") as f:
    document_bytes = f.read()
chunks = chunker.process_document_bytes(document_bytes, "docx")

# Work with chunks
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.metadata['node_type']} - {len(chunk.text)} chars")
    print(f"Headings: {chunk.metadata['headings']}")
```

### Advanced Configuration

```python
from docchunker import DocChunker

# Configure chunk size and overlap for better context preservation
chunker = DocChunker(
    chunk_size=300,           # Target tokens per chunk
    num_overlapping_elements=2 # Elements to overlap between chunks
)

chunks = chunker.process_document("complex_document.pdf")

# Overlap provides better context continuity
for chunk in chunks:
    if chunk.metadata.get('has_overlap'):
        print(f"Overlapped {chunk.metadata['overlap_elements']} elements from previous chunk")
```

### Common Use Cases

```python
from docchunker import DocChunker
from io import BytesIO
import requests

chunker = DocChunker(chunk_size=200, num_overlapping_elements=1)

# 1. Web uploads/API
response = requests.get("https://example.com/document.pdf")
chunks = chunker.process_document_bytes(response.content, "pdf")

# 2. BytesIO objects (direct processor access)
file_obj = BytesIO(document_bytes)
pdf_processor = chunker.processors["pdf"]
chunks = pdf_processor.process(file_obj)

# 3. Database BLOBs
# document_bytes = database.get_document_blob(doc_id)
# chunks = chunker.process_document_bytes(document_bytes, "docx")

# 4. Batch processing
for file_path in ["doc1.docx", "doc2.pdf", "doc3.docx"]:
    chunks = chunker.process_document(file_path)
    print(f"Processed {len(chunks)} chunks from {file_path}")
```

## RAG DEMO
For an end-to-end example of building a simple RAG system using DocChunker with LangChain, check out the `examples/RAG_demo.ipynb` notebook.

## Development

To contribute to DocChunker:

```bash
# Clone the repository
git clone https://github.com/vladGriguta/DocChunker
cd docchunker

# Set up development environment
python -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest
```

## Configuration Parameters

### DocChunker Parameters

- **`chunk_size`** (int, default: 200): Target number of tokens per chunk. Chunks may exceed this size to maintain semantic cohesion.

- **`num_overlapping_elements`** (int, default: 0): Number of elements (list items, table rows) to overlap between adjacent chunks. This provides better context continuity for information retrieval:
  - `0`: No overlap - each element appears in only one chunk
  - `1-3`: Recommended for most use cases - provides context while minimizing duplication  
  - `>3`: High overlap - useful for very context-sensitive applications but increases chunk redundancy

### When to Use Overlap

Use `num_overlapping_elements > 0` when:
- Building RAG systems where context is critical
- Processing documents with closely related list items or table rows
- Working with technical documentation where missing context reduces comprehension

Use `num_overlapping_elements = 0` when:
- Processing very large documents where duplication is costly
- Building simple search indices where exact deduplication is important
- Working with documents where elements are largely independent

## Future Roadmap

- [ ] **Chunk Size Homogenization**: Implement strategies to reduce chunk size variance.
- [ ] **Enhanced Unit Testing**: Add more tests for complex tables and lists.
- [ ] **Retrieval Evaluation Framework**: Develop a framework to assess chunk effectiveness.
- [ ] **Increased Test Coverage**: Systematically improve overall code coverage.
- [x] **PDF Support**: Full PDF parsing and chunking support with structure detection.
- [x] **Element Overlap**: Configurable overlap between chunks for better context preservation.
- [ ] **Advanced Element Handling**: Support for images (captions/alt-text), headers/footers, footnotes.
- [ ] **Performance Optimizations**: Profile and optimize for very large documents.


## License

MIT

## About the Author

DocChunker is developed by **Vlad Griguta**. Connect with me on [LinkedIn](https://www.linkedin.com/in/vlad-marius-griguta) or [GitHub](https://github.com/vladGriguta).