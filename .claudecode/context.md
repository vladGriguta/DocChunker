# DocChunker - Context-Aware Document Chunking Library

## Overview
DocChunker is a specialized Python library designed to intelligently chunk complex documents (DOCX and PDF) while preserving their hierarchical structure and semantic context. Unlike traditional text splitters, DocChunker maintains document hierarchy, keeps related content together (like list items and table rows), and includes contextual information (headings) in each chunk for improved RAG performance.

## Core Architecture

### Key Components
1. **Processors** (`docchunker/processors/`)
   - `BaseProcessor`: Abstract base class defining the processing interface
   - `DocxProcessor`: Orchestrates DOCX parsing and chunking
   - `PdfProcessor`: Placeholder for PDF processing (TO BE IMPLEMENTED)

2. **DOCX Processing Pipeline** 
   - `DocxParser`: Parses DOCX into hierarchical structure with proper list detection (using XML numbering)
   - `DocxChunker`: Converts hierarchical elements into context-aware chunks with heading preservation

3. **Models** (`docchunker/models/`)
   - `Chunk`: Data class representing a text chunk with metadata (type, headings, token count)

### Document Structure Representation
Documents are parsed into a hierarchical tree where each node has:
- `type`: heading, paragraph, list_container, list_item, table
- `level`: depth/indentation level (0-indexed for lists)
- `content`: text content or structured data (tables have header/data_rows)
- `children`: nested elements
- `num_id`: numbering ID for list items (-1 for style-based detection)

### Chunking Strategy
1. **Context Preservation**: Each chunk includes all parent headings (H1, H2, etc.)
2. **Semantic Grouping**: 
   - List items stay together until chunk size limit
   - Table rows are chunked together with headers repeated
3. **Size Control**: Token-based chunking using tiktoken (cl100k_base encoding)
4. **Overlap Support**: Planned feature for maintaining context across chunk boundaries

## Current Implementation Status

### Working Features
- ✅ DOCX parsing with complex nested lists and tables
- ✅ Hierarchical structure preservation
- ✅ Token-based chunk size control
- ✅ Context-aware chunking with heading preservation
- ✅ Table chunking with header repetition
- ✅ List container splitting when exceeding chunk size
- ✅ YAML-driven testing framework

### Known Issues
1. **File Input Limitation**: Can only load files from disk, not from in-memory DOCX objects
2. **PDF Support**: Not implemented yet
3. **Overlapping Elements**: `num_overlapping_elements` parameter not implemented
4. **Large Single Elements**: Oversized paragraphs/tables aren't split (TODO comment in code)

## Testing Infrastructure
- YAML-driven test framework in `data/unittests/`
- Test files pair `.docx` documents with `.yaml` configurations
- Tests verify chunk content, context preservation, and metadata accuracy

## Immediate Development Goals

### Priority 1: Fix File Input Limitation
**Current Issue**: `DocChunker.process_document()` only accepts file paths
**Goal**: Support in-memory DOCX processing
**Impact**: 
- Enables processing of uploaded files without disk I/O
- Important for web applications and API integrations
- Requires updating documentation and PyPI package

### Priority 2: PDF Support Implementation
**Current State**: `PdfProcessor` exists but raises NotImplementedError
**Goal**: Basic PDF parsing and chunking with same context-aware format
**Approach**:
- Start with simple text extraction
- Detect headings through font size/style analysis
- Apply same hierarchical chunking logic as DOCX
- Maintain consistent chunk output format

### Priority 3: Implement Overlapping Elements
**Current State**: Parameter exists but raises NotImplementedError
**Goal**: Add context overlap between chunks for better coherence
**Implementation**:
- For lists: Include last N items from previous chunk
- For tables: Include last N rows from previous chunk
- Ensure overlap doesn't create duplicate content issues

## Code Quality Notes
- Uses type hints throughout
- Token counting cached with `@lru_cache`
- Extensive use of recursive processing for hierarchical structures
- Debug outputs via `write_json()` for parsed and chunked elements

## Dependencies
- Core: `python-docx`, `tiktoken`
- PDF (future): `pypdf` already in requirements
- Testing: `pytest`, `pyyaml`
- Optional: LangChain integration for RAG demos

## Development Workflow
1. Parser extracts document structure
2. Chunker processes hierarchical elements
3. Chunks include full heading context
4. Metadata tracks chunk type and token count
5. YAML tests verify expected behavior

## Important Design Decisions
- **Token-based sizing** instead of character count for LLM compatibility
- **Heading context** always included to maintain document structure awareness
- **Recursive processing** to handle arbitrary nesting depth
- **Separate parsing and chunking** phases for modularity