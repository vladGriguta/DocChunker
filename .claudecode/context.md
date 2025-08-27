# DocChunker - Context-Aware Document Chunking Library

## Overview
DocChunker is a specialized Python library designed to intelligently chunk complex documents (DOCX and PDF) while preserving their hierarchical structure and semantic context. Unlike traditional text splitters, DocChunker maintains document hierarchy, keeps related content together (like list items and table rows), and includes contextual information (headings) in each chunk for improved RAG performance.

**Current Version**: 0.2.0 - Full PDF support with sophisticated structure detection and configurable element overlap functionality.

## Core Architecture

### Key Components
1. **Processors** (`docchunker/processors/`)
   - `BaseProcessor`: Abstract base class defining the processing interface
   - `DocxProcessor`: Orchestrates DOCX parsing and chunking
   - `PdfProcessor`: Full PDF processing with intelligent structure detection

2. **Document Processing Pipelines**
   - `DocxParser`: Parses DOCX into hierarchical structure with proper list detection (using XML numbering)
   - `PdfParser`: Extracts PDF structure using PyMuPDF with paragraph consolidation and multi-signal heading detection
   - `DocumentChunker`: Format-agnostic chunker that converts hierarchical elements into context-aware chunks with heading preservation

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
4. **Overlap Support**: Configurable overlap between chunks with intelligent management for lists and tables

## Current Implementation Status

### Working Features
- ✅ **DOCX Processing**: Complete support with complex nested lists and tables
- ✅ **PDF Processing**: Full support with intelligent structure detection
  - PyMuPDF integration with PyPDF fallback
  - Paragraph consolidation using bbox analysis and formatting consistency
  - Multi-signal heading detection (font size, bold, positioning, content patterns)
  - Advanced list detection with indentation analysis
- ✅ **Hierarchical Structure Preservation**: Maintains document hierarchy across formats
- ✅ **Token-based Chunk Size Control**: Accurate sizing using tiktoken
- ✅ **Context-aware Chunking**: Heading preservation across all chunks
- ✅ **Table Chunking**: Row-based splitting with header repetition
- ✅ **List Container Splitting**: Smart chunking when exceeding size limits
- ✅ **Element Overlap Functionality**: Configurable overlap with metadata tracking
  - Overlap between list items and table rows
  - Intelligent overlap management preventing infinite loops
  - Metadata fields: `has_overlap`, `overlap_elements`
- ✅ **Enhanced Testing Infrastructure**: YAML-driven framework with format-specific xfail flags
- ✅ **Flexible Input Methods**: File paths, bytes, and BytesIO objects
- ✅ **Unified Architecture**: Format-agnostic DocumentChunker for consistent behavior

### Known Issues
1. **File Input Limitation**: Can only load files from disk, not from in-memory DOCX objects
2. **Large Single Elements**: Oversized paragraphs/tables aren't split (TODO comment in code)
3. **PDF Table Detection**: Basic table detection implemented but could be enhanced with position-based analysis
4. **Format-Specific Optimizations**: While unified chunking works well, some format-specific optimizations could potentially improve quality

## Testing Infrastructure
- **YAML-driven Framework**: Comprehensive test suite in `data/unittests/`
- **Cross-format Testing**: Test files pair both `.docx` and `.pdf` documents with `.yaml` configurations
- **Source-specific Expectations**: xfail flags (`xfail_pdf`, `xfail_docx`) for tracking format-specific capabilities
- **Comprehensive Coverage**: Tests verify chunk content, context preservation, metadata accuracy, and overlap functionality
- **Current Status**: 32 tests passing, 6 expected failures (xfail) for format-specific edge cases

## Current Development Goals

### Priority 1: Enhanced File Input Support
**Current Issue**: `DocChunker.process_document()` only accepts file paths
**Goal**: Support in-memory document processing for both DOCX and PDF
**Impact**: 
- Enables processing of uploaded files without disk I/O
- Important for web applications and API integrations
- Requires extending `process_document_bytes()` method

### Priority 2: Advanced PDF Structure Detection
**Current State**: Basic PDF parsing working well, but could be enhanced
**Goal**: Improve table detection and complex layout handling
**Approach**:
- Implement position-based table detection using bbox coordinates
- Enhance multi-column layout detection
- Improve figure/image caption detection
- Add better handling of headers/footers

### Priority 3: Performance Optimizations
**Current Focus**: Optimize processing speed for large documents
**Implementation Ideas**:
- Cache font statistics calculation for PDF processing
- Optimize token counting with better caching strategies
- Consider streaming processing for very large documents
- Profile and optimize paragraph consolidation algorithms

### Priority 4: Format-Specific Enhancements
**Goal**: Leverage the `source_format` parameter for targeted improvements
**Potential Areas**:
- DOCX-specific: Better handling of embedded objects and comments
- PDF-specific: Enhanced heading detection using document outline/bookmarks
- Cross-format: Improved metadata extraction and preservation

## Code Quality Notes
- **Type Safety**: Comprehensive type hints throughout codebase
- **Performance**: Token counting cached with `@lru_cache`, optimized bbox analysis
- **Architecture**: Extensive recursive processing for hierarchical structures
- **Debugging**: Debug outputs via `write_json()` for parsed and chunked elements
- **Format Consistency**: Unified chunking logic ensures consistent output across formats
- **Error Handling**: Graceful fallbacks (PyMuPDF → PyPDF, enhanced heuristics)
- **Testing**: 60%+ improvement in PDF chunk quality through paragraph consolidation

## Dependencies
- **Core**: `python-docx>=0.8.11`, `tiktoken>=0.9.0`, `pypdf>=3.15.1`, `pymupdf>=1.23.0`
- **Testing**: `pytest>=7.4.0`, `pyyaml>=6.0.2`, `pytest-cov>=4.1.0`
- **Development**: `mypy>=1.5.1`, `black>=23.9.1`, `isort>=5.12.0`, `ruff>=0.0.292`
- **Optional**: LangChain integration for RAG demos, Jupyter notebooks for examples

## Development Workflow (v0.2.0)
1. **Format Detection**: Automatic DOCX/PDF format handling
2. **Structure Extraction**: 
   - DOCX: XML-based parsing with proper list/table detection
   - PDF: PyMuPDF extraction with bbox analysis and paragraph consolidation
3. **Unified Chunking**: DocumentChunker processes hierarchical elements consistently
4. **Context Preservation**: All chunks include full heading hierarchy
5. **Overlap Management**: Configurable overlap with intelligent deduplication
6. **Metadata Enrichment**: Comprehensive tracking (chunk type, tokens, overlap status)
7. **Quality Assurance**: YAML-driven tests with format-specific validation

## Important Design Decisions
- **Token-based sizing** instead of character count for LLM compatibility
- **Heading context** always included to maintain document structure awareness
- **Recursive processing** to handle arbitrary nesting depth
- **Unified chunking architecture**: Format-agnostic DocumentChunker ensures consistency
- **Separate parsing and chunking** phases for modularity and maintainability
- **Paragraph consolidation**: Sophisticated spatial and formatting analysis for PDF coherence
- **Multi-signal detection**: Heading detection uses font size, formatting, content, and positioning
- **Intelligent overlap**: Context preservation without infinite loops or excessive duplication