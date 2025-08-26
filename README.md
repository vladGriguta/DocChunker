# DocChunker

A specialized document chunking library designed to handle complex document structures in DOCX and PDF files. DocChunker intelligently processes structured documents containing tables, nested lists, images, and other complex elements to create semantically meaningful chunks that preserve context.

DocChunker supports flexible input methods - process documents from file paths, raw bytes, or file-like objects, making it ideal for web applications, database integration, and cloud-based document processing pipelines.

## Key Features

*   **In-Memory Processing**: Process documents from bytes, BytesIO objects, or file paths - perfect for web uploads, databases, and cloud storage.
*   **Advanced DOCX Parsing**: Handles complex elements like nested lists and tables with merged cells.
*   **Contextual Chunking**: Preserves document hierarchy (headings, etc.) within chunks.
*   **Configurable Strategy**: Tune chunk size (tokens) and element-based overlap.
*   **Semantic Cohesion**: Aims to keep related content (list items, table rows) together.
*   **RAG-Optimized**: Produces chunks ideal for effective information retrieval.

## Installation

DocChunker requires Python 3.9+ and is best installed using [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with uv
uv pip install -r requirements.txt
```

## Quick Start

```python
from docchunker import DocChunker

# Initialize the chunker with desired settings
chunker = DocChunker(chunk_size=200)

# Read document bytes (from file, web request, database, etc.)
with open("complex_document.docx", "rb") as f:
    document_bytes = f.read()

# Process the document from bytes
chunks = chunker.process_document_bytes(document_bytes, file_format="docx")

# Work with chunks
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.metadata['type']} - {len(chunk.text)} chars")
```

### Processing from File Path

You can also process documents directly from file paths:

```python
from docchunker import DocChunker

chunker = DocChunker(chunk_size=200)
chunks = chunker.process_document("complex_document.docx")
```

### Common Use Cases

```python
from docchunker import DocChunker
from io import BytesIO
import requests

chunker = DocChunker(chunk_size=200)

# 1. From web upload/API
response = requests.get("https://example.com/document.docx")
chunks = chunker.process_document_bytes(response.content, "docx")

# 2. From BytesIO object
file_obj = BytesIO(document_bytes)
docx_processor = chunker.processors["docx"]
chunks = docx_processor.process(file_obj)

# 3. From database BLOB
# document_bytes = database.get_document_blob(doc_id)
# chunks = chunker.process_document_bytes(document_bytes, "docx")
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

## Future Roadmap

- [ ] **Chunk Size Homogenization**: Implement strategies to reduce chunk size variance.
- [ ] **Langchain RAG Examples**: Provide integration guides for Langchain.
- [ ] **Enhanced Unit Testing**: Add more tests for complex tables and lists.
- [ ] **Retrieval Evaluation Framework**: Develop a framework to assess chunk effectiveness.
- [ ] **Increased Test Coverage**: Systematically improve overall code coverage.
- [ ] **PDF Support**: Extend parsing and chunking to PDF documents.
- [ ] **Advanced Element Handling**: Support for images (captions/alt-text), headers/footers, footnotes.
- [ ] **Performance Optimizations**: Profile and optimize for very large documents.


## License

MIT

## About the Author

DocChunker is developed by **Vlad Griguta**. Connect with me on [LinkedIn](https://www.linkedin.com/in/vlad-marius-griguta) or [GitHub](https://github.com/vladGriguta).