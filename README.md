# DocChunker

A specialized document chunking library designed to handle complex document structures in DOCX and PDF files. DocChunker intelligently processes structured documents containing tables, nested lists, images, and other complex elements to create semantically meaningful chunks that preserve context.

DocChunker supports flexible input methods - process documents from file paths, raw bytes, or file-like objects, making it ideal for web applications, database integration, and cloud-based document processing pipelines.

## Key Features

*   **In-Memory Processing**: Process documents from bytes, BytesIO objects, or file paths - perfect for web uploads, databases, and cloud storage.
*   **Multi-Format Support**: Full support for DOCX and PDF documents with intelligent structure detection.
*   **Advanced Document Parsing**: Handles complex elements like nested lists, tables with merged cells, headings, and paragraphs.
*   **Contextual Chunking**: Preserves document hierarchy (headings, etc.) within chunks for better semantic understanding.
*   **Overlap Control**: Configure element-based overlap between chunks to maintain context continuity.
*   **Configurable Strategy**: Tune chunk size (characters) and overlap parameters for optimal performance.
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
chunker = DocChunker(chunk_size=1000)

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
    chunk_size=1500,          # Target characters per chunk
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

chunker = DocChunker(chunk_size=1000, num_overlapping_elements=1)

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

## Evaluating Retrieval Quality

DocChunker ships a dependency-light evaluation framework to answer: "given this document and these queries, how well do the produced chunks support retrieval?" It includes a from-scratch BM25 retriever (no ML dependencies) and a config comparison helper to pick chunking parameters empirically.

```python
from docchunker import (
    DocChunker, EvalDataset, EvalQuery, RetrievalEvaluator, compare_configs,
)

dataset = EvalDataset(
    document_path="document.docx",
    queries=[
        EvalQuery(query="how does password recovery work",
                  expected_substring="Password recovery"),
        EvalQuery(query="which department owns the frontend",
                  expected_keywords=["Frontend Team", "Engineering"]),
    ],
)
# Datasets can also be loaded from JSON/YAML: EvalDataset.from_file("eval.yaml")

# Evaluate one configuration
evaluator = RetrievalEvaluator(DocChunker(chunk_size=500))
report = evaluator.evaluate(dataset, k=5)
print(report)  # hit_rate@5, MRR, chunk size stats, per-query ranks

# Compare chunking configurations empirically
comparison = compare_configs(
    "document.docx", dataset,
    configs=[{"chunk_size": 300}, {"chunk_size": 1000, "num_overlapping_elements": 1}],
)
print(comparison)          # table: chunks, mean size, hit_rate@k, MRR per config
print(comparison.best())   # top-scoring config
```

To evaluate with an embedding-based retriever, implement the `Retriever` protocol (`index(chunks)` and `retrieve(query, k)`) and pass it to `RetrievalEvaluator` — DocChunker adds no embedding dependency. See `examples/retrieval_evaluation_demo.py` for a runnable end-to-end example.

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

- **`chunk_size`** (int, default: 1000): Target number of characters per chunk. Chunks may exceed this size to maintain semantic cohesion.

- **`min_chunk_size`** (int, default: `chunk_size // 4`): Minimum target number of characters per paragraph chunk. Consecutive small paragraphs under the same heading context are merged into a single chunk (metadata `node_type: "paragraph_group"`) until this size is reached, while the combined chunk stays within `chunk_size`. Single paragraphs larger than `chunk_size` are split at sentence boundaries into multiple chunks (metadata `is_split`, `split_index`, `split_total`). Set to `1` to effectively disable paragraph merging. Only affects paragraph chunks; table and list chunking are unchanged.

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

- [x] **Chunk Size Homogenization**: Implement strategies to reduce chunk size variance.
- [ ] **Enhanced Unit Testing**: Add more tests for complex tables and lists.
- [x] **Retrieval Evaluation Framework**: Develop a framework to assess chunk effectiveness.
- [ ] **Increased Test Coverage**: Systematically improve overall code coverage.
- [x] **PDF Support**: Full PDF parsing and chunking support with structure detection.
- [x] **Element Overlap**: Configurable overlap between chunks for better context preservation.
- [ ] **Advanced Element Handling**: Support for images (captions/alt-text), headers/footers, footnotes.
- [ ] **Performance Optimizations**: Profile and optimize for very large documents.


## License

MIT

## About the Author

DocChunker is developed by **Vlad Griguta**. Connect with me on [LinkedIn](https://www.linkedin.com/in/vlad-marius-griguta) or [GitHub](https://github.com/vladGriguta).