# DocChunker

A specialized document chunking library designed to handle complex document structures in DOCX and PDF files. DocChunker intelligently processes structured documents containing tables, nested lists, images, and other complex elements to create semantically meaningful chunks that preserve context.

## Key Features

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

# Process a document
chunks = chunker.process_document("complex_document.docx")

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.metadata['type']} - {len(chunk.text)} chars")
```

## RAG DEMO
For an end-to-end example of building a simple RAG system using DocChunker with LangChain, check out the examples/RAG_demo.ipynb notebook.

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