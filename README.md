# DocChunker

A specialized document chunking library designed to handle complex document structures in DOCX and PDF files. DocChunker intelligently processes structured documents containing tables, nested lists, images, and other complex elements to create semantically meaningful chunks that preserve context.

## Features

- **Structure-aware chunking**: Preserves semantic boundaries and document structure
- **Complex element handling**: Specialized processing for tables, nested lists, images, etc.
- **Multi-format support**: Works with DOCX, PDF, and other document formats
- **Context preservation**: Maintains relationships between document elements
- **Customizable chunk size**: Adjustable chunk sizes with intelligent overlap
- **Azure integration**: Optional Azure AI services integration for enhanced processing

## Installation

DocChunker requires Python 3.9+ and is best installed using [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

# Install with uv
uv pip install -r requirements.txt
```

## Quick Start

```python
from docchunker import DocChunker

# Initialize the chunker with desired settings
chunker = DocChunker(
    chunk_size=1000,
    chunk_overlap=200,
    preserve_structure=True
)

# Process a document
chunks = chunker.process_document("complex_document.docx")

# Work with chunks
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {chunk.metadata['type']} - {len(chunk.text)} chars")
```

## Development

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

## License

MIT