# DocChunker Unit Tests Guide

This directory contains test documents and configurations for validating DocChunker's behavior using a YAML-driven testing framework.

## Overview

The testing approach uses **document triplets**: each test consists of a `.docx` file, a `.pdf` file (converted from the DOCX), and a corresponding `.yaml` configuration file that defines expected chunking behavior for both formats.

### Format-Specific Testing

DocChunker supports both DOCX and PDF processing, but these formats have different capabilities:

- **DOCX**: Rich semantic information (lists, headings, tables with structure)
- **PDF**: Limited semantic information (text extraction with basic formatting)

The YAML configuration allows format-specific expected failures using `xfail_docx` and `xfail_pdf` flags, letting us track known limitations for each format.

```
data/unittests/
├── README.md                    # This guide
├── nested_lists.docx            # Test document with complex nested lists
├── nested_lists.pdf             # PDF version of the above
├── sample_table.docx            # Test document with tables
├── sample_table.pdf             # PDF version of the above
├── test_nested_lists.yaml       # Test configuration for nested lists
└── test_sample_table.yaml       # Test configuration for table document
```

## Quick Start

### Running Tests

```bash
# Run all DOCX tests
pytest tests/test_docx_processor.py -v

# Run all PDF tests
pytest tests/test_pdf_processor.py -v

# Run both formats
pytest tests/test_docx_processor.py tests/test_pdf_processor.py -v
```

### Test Results

- ✅ **PASS**: Test case meets expectations
- ❌ **FAIL**: Test case fails (needs DocChunker fixes)
- ⚠️ **XFAIL**: Expected failure (marked with `xfail: true`)

## YAML Configuration Format

### Basic Structure

```yaml
document: "your_test_file.docx"
description: "Brief description of what this tests"

test_cases:
  - name: "descriptive_test_name"
    search_text: "Text to find in chunks"
    expected_in_chunk:
      - "Other text that should be in same chunk"
    expected_metadata:
      type: "expected_chunk_type"
    xfail: true  # Optional: mark as expected failure

global_checks:
  min_chunks: 10
  max_empty_chunks: 0
```

### Test Case Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `name` | Yes | Unique test identifier | `"password_recovery_context"` |
| `search_text` | Yes | Text to search for in chunks | `"Password recovery"` |
| `expected_in_chunk` | No | List of text that should appear in same chunk | `["Section 2:", "Development workflow:"]` |
| `expected_metadata` | No | Expected metadata fields | `type: "list", depth: 2` |
| `xfail` | No | Mark as expected failure for all formats | `true` |
| `xfail_docx` | No | Mark as expected failure for DOCX only | `true` |
| `xfail_pdf` | No | Mark as expected failure for PDF only | `true` |

### Global Checks

| Field | Description | Example |
|-------|-------------|---------|
| `min_chunks` | Minimum number of chunks expected | `10` |
| `min_list_items` | Minimum number of list chunks | `20` |
| `max_empty_chunks` | Maximum allowed empty chunks | `0` |
| `chunk_types` | Required chunk types | `["heading", "text", "list"]` |

## Adding New Test Cases

### Step 1: Create Test Document

Create a `.docx` file with specific features you want to test:

```
data/unittests/test_my_feature.docx
```

**Tips for good test documents:**
- Include clear section headers for context testing
- Use realistic content that represents actual use cases
- Test edge cases (very long lists, complex tables, etc.)
- Keep documents focused on specific features

### Step 2: Create YAML Configuration

Create corresponding `.yaml` file:

```yaml
document: "test_my_feature.docx"
description: "Tests [specific feature] processing"

test_cases:
  - name: "meaningful_test_name"
    search_text: "Specific content to find"
    expected_in_chunk:
      - "Context that should be preserved"
    expected_metadata:
      type: "expected_type"

global_checks:
  min_chunks: 5
```

### Step 3: Run and Iterate

```bash
# Test your new configuration
python tests/test_yaml_driven.py

# Mark failing tests as expected during development
xfail: true
```

## Test-Driven Development Workflow

### 1. Define Expected Behavior
Create YAML config with expected chunking behavior:
```yaml
test_cases:
  - name: "table_headers_preserved"
    search_text: "Q1 Revenue"
    expected_in_chunk:
      - "Performance Data"
      - "Metric | Q1 | Q2 | Q3"
    expected_metadata:
      type: "table"
    xfail: true  # Expected to fail initially
```

### 2. Run Tests (Red)
```bash
pytest tests/test_yaml_driven.py -v
# Should show failures for new features
```

### 3. Implement Features (Green)
Fix DocChunker code until tests pass:
- Update processor logic
- Fix metadata generation
- Improve context preservation

### 4. Remove xfail (Refactor)
Once tests pass, remove `xfail: true` from YAML:
```yaml
test_cases:
  - name: "table_headers_preserved"
    # ... same config but remove xfail line
```

## Common Test Patterns

### Context Preservation
Test that related content stays together:
```yaml
- name: "list_with_context"
  search_text: "Important task"
  expected_in_chunk:
    - "Section Header"
    - "Introduction text"
```

### Metadata Accuracy
Verify chunk types and properties:
```yaml
- name: "heading_detection"
  search_text: "Chapter 1"
  expected_metadata:
    type: "heading"
    level: 1
```

### Structure Validation
Check overall document processing:
```yaml
global_checks:
  chunk_types: ["heading", "text", "list", "table"]
  min_chunks: 20
  max_empty_chunks: 0
```

## Example: Complete Test Case

**Document**: Complex project plan with sections, lists, and tables

**YAML Configuration**:
```yaml
document: "test_project_plan.docx"
description: "Tests project management document with mixed content"

test_cases:
  - name: "task_hierarchy"
    search_text: "Backend API development"
    expected_in_chunk:
      - "Development Phase"
      - "Technical Tasks"
    expected_metadata:
      type: "list"
      depth: 2

  - name: "budget_table"
    search_text: "$50,000"
    expected_in_chunk:
      - "Budget Overview"
      - "Department | Q1 | Q2"
    expected_metadata:
      type: "table"

global_checks:
  min_chunks: 15
  chunk_types: ["heading", "text", "list", "table"]
  max_empty_chunks: 0
```

## Debugging Failed Tests

### 1. Run Manual Inspection
```bash
python tests/test_yaml_driven.py
```
This shows detailed output about what was found vs. expected.

### 2. Check Document Structure
Open the `.docx` file and verify:
- Is the search text actually there?
- Is the expected context in the same logical section?
- Are the styles applied correctly (List Bullet, Heading 1, etc.)?

### 3. Adjust Expectations
Sometimes the test expectations need refinement:
- Context might be split across chunks legitimately
- Metadata might be different than expected
- Document structure might need adjustment

### 4. Mark as xfail Temporarily
While developing features, mark tests as expected failures:
```yaml
# For all formats:
xfail: true  # Remove when feature is implemented

# For specific formats (useful when PDF has limitations):
xfail_pdf: true    # PDF format has known limitations
xfail_docx: true   # DOCX processing needs work

# Example: PDF can't detect certain structures but DOCX can
- name: "complex_table_detection"
  search_text: "Nested table data"
  xfail_pdf: true  # PDF format loses table structure
```

## Best Practices

### Writing Good Tests
- **Specific**: Test one feature per document
- **Realistic**: Use actual document patterns
- **Focused**: Don't test everything in one document
- **Clear**: Use descriptive names and comments

### Maintaining Tests
- **Version control**: Commit both `.docx` and `.yaml` files
- **Documentation**: Update this README when adding new patterns
- **Cleanup**: Remove `xfail` flags when features work
- **Review**: Periodically check if tests still reflect requirements

## Troubleshooting

### Test File Not Found
```
pytest.skip: Test file not found: test_example.docx
```
**Solution**: Ensure `.docx` file exists in `data/unittests/`

### No Matching Chunks
```
AssertionError: No chunks found containing 'search text'
```
**Solutions**:
- Check spelling in search text
- Verify text exists in document
- Check if text is split across formatting boundaries

### Context Not Preserved
```
AssertionError: Expected 'Section Header' in same chunk as 'list item'
```
**Solutions**:
- Adjust chunk size settings
- Check if content is naturally in different sections
- Verify document structure matches expectations

### Metadata Mismatch
```
AssertionError: Expected type='list', got 'text'
```
**Solutions**:
- Check document formatting (ensure proper list styles)
- Verify DocChunker list detection logic
- Adjust expected metadata to match reality

---

## Contributing

When adding new test cases:

1. **Create focused documents** that test specific features
2. **Write clear YAML configs** with descriptive names
3. **Start with xfail** for new features under development
4. **Update this README** if you introduce new testing patterns
5. **Test your tests** - make sure they fail when they should!

Happy testing! 🧪