# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-08-27

### Added
- **PDF Support**: Full PDF document processing with intelligent structure detection
  - New `PdfParser` class for extracting text and detecting document structure from PDF files
  - Font-size based heading detection heuristics  
  - Indentation and bullet pattern list identification
  - Support for PDF processing through all existing methods (`process_document`, `process_document_bytes`, etc.)
  - PDF chunks maintain identical metadata structure to DOCX chunks

- **Element Overlap Functionality**: Configurable overlap between chunks for better context preservation
  - New `num_overlapping_elements` parameter in `DocChunker` constructor
  - Overlapping elements for list items and table rows to maintain context continuity
  - Overlap metadata tracking: `has_overlap` and `overlap_elements` fields in chunk metadata
  - Intelligent overlap management prevents infinite loops and excessive duplication

- **Enhanced Testing Infrastructure**:
  - YAML-driven test framework with source-specific expected failures (`xfail_pdf`, `xfail_docx`)
  - Comprehensive PDF test suite mirroring DOCX functionality
  - Overlap functionality tests covering basic usage, metadata tracking, and edge cases
  - Duck typing tests for flexible input handling (file paths vs BytesIO objects)

### Changed
- **Dependencies**: Moved `pypdf>=3.15.1` from dev dependencies to core dependencies
- **Documentation**: Updated README.md with PDF support examples and overlap parameter documentation
- **Version**: Bumped to 0.2.0 reflecting significant new functionality

### Technical Details
- PDF processing reuses existing `DocxChunker` logic ensuring consistency across formats
- Overlap implementation maintains token counting accuracy and chunk size constraints  
- Source-specific xfail flags allow tracking format-specific capabilities and limitations
- All existing functionality remains unchanged - no breaking changes

### Testing
- 29 tests passing, 6 expected failures (xfail) for format-specific edge cases
- Full test coverage for new PDF and overlap functionality
- Backward compatibility validated for all existing DOCX processing workflows

## [0.1.4] - 2024-XX-XX

### Added
- Initial DOCX processing functionality
- Context-aware chunking with heading preservation
- Flexible input methods (file paths, bytes, BytesIO objects)
- Basic table and list processing
- RAG-optimized chunk generation

### Technical Implementation
- `DocxParser` for DOCX structure extraction
- `DocxChunker` for intelligent chunking
- Token-based chunk sizing with tiktoken
- Hierarchical document structure preservation