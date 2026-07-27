"""Direct unit tests for DocumentChunker.apply() using synthetic node dicts.

These tests exercise the format-agnostic chunk consolidation logic without
going through a parser, covering edge cases that real documents rarely hit:
empty inputs, degenerate tables/lists, unknown node types and heading-level
gaps.

Note: assertions here are deliberately structural (content presence, heading
context, metadata keys) rather than pinning exact chunk sizes, since the
size-homogenization strategy may evolve.
"""

import pytest

from docchunker.models.chunk import Chunk
from docchunker.processors.document_chunker import DocumentChunker

DOC_ID = "synthetic-doc"


def make_chunker(chunk_size: int = 1000, overlap: int = 0) -> DocumentChunker:
    return DocumentChunker(chunk_size=chunk_size, num_overlapping_elements=overlap)


def paragraph(content: str, level: int = 0) -> dict:
    return {"type": "paragraph", "level": level, "content": content, "children": []}


def heading(content: str, level: int, children: list | None = None) -> dict:
    return {"type": "heading", "level": level, "content": content, "children": children or []}


def list_item(content: str, level: int = 0, num_id: int = 1, children: list | None = None) -> dict:
    return {
        "type": "list_item",
        "level": level,
        "num_id": num_id,
        "content": content,
        "children": children or [],
    }


class TestApplyDegenerateInputs:
    def test_empty_input_returns_empty_list(self):
        assert make_chunker().apply([], DOC_ID) == []

    def test_unknown_node_type_is_ignored(self):
        nodes = [{"type": "comment", "content": "should not appear", "children": []}]
        assert make_chunker().apply(nodes, DOC_ID) == []

    def test_node_without_type_is_ignored(self):
        nodes = [{"content": "typeless node", "children": []}]
        assert make_chunker().apply(nodes, DOC_ID) == []

    def test_heading_without_children_produces_no_chunk(self):
        nodes = [heading("Lonely Heading", level=1)]
        assert make_chunker().apply(nodes, DOC_ID) == []

    def test_list_container_without_children_produces_no_chunk(self):
        nodes = [{"type": "list_container", "level": 0, "num_id": 1, "children": []}]
        assert make_chunker().apply(nodes, DOC_ID) == []

    def test_table_without_header_or_rows_produces_no_chunk(self):
        nodes = [{"type": "table", "header": [], "data_rows": [], "children": []}]
        assert make_chunker().apply(nodes, DOC_ID) == []

    def test_whitespace_only_paragraph_produces_no_chunk(self):
        nodes = [paragraph("   \n  ")]
        assert make_chunker().apply(nodes, DOC_ID) == []


class TestApplyTables:
    def test_header_only_table_emits_header_chunk(self):
        nodes = [{"type": "table", "header": ["Alpha", "Beta"], "data_rows": [], "children": []}]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "table_header_only"
        assert "Table Header: Alpha | Beta" in chunks[0].text
        assert chunks[0].metadata["document_id"] == DOC_ID

    def test_table_row_pairs_cells_with_header_labels(self):
        nodes = [{
            "type": "table",
            "header": ["Name", "Role"],
            "data_rows": [["Ada", "Engineer"]],
            "children": [],
        }]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "table_rows"
        assert "Name: Ada" in chunks[0].text
        assert "Role: Engineer" in chunks[0].text

    def test_mismatched_header_falls_back_to_joined_row(self):
        nodes = [{
            "type": "table",
            "header": ["OnlyOne"],
            "data_rows": [["a", "b", "c"]],
            "children": [],
        }]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert "a | b | c" in chunks[0].text
        # Header labels cannot be paired when lengths mismatch.
        assert "OnlyOne:" not in chunks[0].text

    def test_missing_header_falls_back_to_joined_row(self):
        nodes = [{
            "type": "table",
            "header": [],
            "data_rows": [["x", "y"]],
            "children": [],
        }]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert "x | y" in chunks[0].text

    def test_non_string_cells_without_header_raise_value_error(self):
        # Current contract: when the header cannot be paired and cells are not
        # strings, the fallback join fails and a ValueError is raised.
        nodes = [{
            "type": "table",
            "header": [],
            "data_rows": [[1, 2]],
            "children": [],
        }]
        with pytest.raises(ValueError, match="Row data must be a list of strings"):
            make_chunker().apply(nodes, DOC_ID)

    def test_large_table_splits_with_header_repeated_in_every_chunk(self):
        rows = [[f"item-{i:02d}", "x" * 80] for i in range(20)]
        nodes = [{"type": "table", "header": ["Key", "Value"], "data_rows": rows, "children": []}]
        chunks = make_chunker(chunk_size=300).apply(nodes, DOC_ID)

        table_chunks = [c for c in chunks if c.metadata["node_type"] == "table_rows"]
        assert len(table_chunks) >= 2, "Large table should split into multiple chunks"
        combined = "\n".join(c.text for c in table_chunks)
        for i in range(20):
            assert f"item-{i:02d}" in combined, "No row may be lost when splitting"
        for chunk in table_chunks:
            assert "Key:" in chunk.text, "Header labels must repeat in every chunk"

    def test_table_overlap_metadata_and_repeated_rows(self):
        rows = [[f"row-{i:02d}", "y" * 80] for i in range(10)]
        nodes = [{"type": "table", "header": ["Id", "Data"], "data_rows": rows, "children": []}]
        chunks = make_chunker(chunk_size=300, overlap=1).apply(nodes, DOC_ID)

        table_chunks = [c for c in chunks if c.metadata["node_type"] == "table_rows"]
        assert len(table_chunks) >= 2
        assert table_chunks[0].metadata["has_overlap"] is False
        assert table_chunks[0].metadata["overlap_elements"] == 0
        for prev, curr in zip(table_chunks, table_chunks[1:]):
            assert curr.metadata["has_overlap"] is True
            assert curr.metadata["overlap_elements"] >= 1
            # The last row of the previous chunk is repeated in the next one.
            last_row_line = prev.text.rstrip().splitlines()[-1]
            assert last_row_line in curr.text


class TestApplyLists:
    def test_list_container_chunk_contains_all_items(self):
        container = {
            "type": "list_container",
            "level": 0,
            "num_id": 1,
            "children": [list_item(f"task number {i}") for i in range(3)],
        }
        chunks = make_chunker().apply([container], DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "list_container"
        for i in range(3):
            assert f"task number {i}" in chunks[0].text

    def test_nested_list_items_are_indented(self):
        child = list_item("nested child item", level=1)
        parent = list_item("top level item", level=0, children=[child])
        container = {"type": "list_container", "level": 0, "num_id": 1, "children": [parent]}
        chunks = make_chunker().apply([container], DOC_ID)

        assert len(chunks) == 1
        lines = chunks[0].text.splitlines()
        parent_line = next(l for l in lines if "top level item" in l)
        child_line = next(l for l in lines if "nested child item" in l)
        parent_indent = len(parent_line) - len(parent_line.lstrip())
        child_indent = len(child_line) - len(child_line.lstrip())
        assert child_indent > parent_indent

    def test_long_list_splits_without_losing_items(self):
        container = {
            "type": "list_container",
            "level": 0,
            "num_id": 1,
            "children": [list_item(f"entry-{i:02d} " + "z" * 60) for i in range(15)],
        }
        chunks = make_chunker(chunk_size=300).apply([container], DOC_ID)

        list_chunks = [c for c in chunks if c.metadata["node_type"] == "list_container"]
        assert len(list_chunks) >= 2, "Long list should split into multiple chunks"
        combined = "\n".join(c.text for c in list_chunks)
        for i in range(15):
            assert f"entry-{i:02d}" in combined

    def test_list_overlap_metadata(self):
        container = {
            "type": "list_container",
            "level": 0,
            "num_id": 1,
            "children": [list_item(f"entry-{i:02d} " + "z" * 60) for i in range(12)],
        }
        chunks = make_chunker(chunk_size=300, overlap=2).apply([container], DOC_ID)

        list_chunks = [c for c in chunks if c.metadata["node_type"] == "list_container"]
        assert len(list_chunks) >= 2
        assert list_chunks[0].metadata["has_overlap"] is False
        for chunk in list_chunks[1:]:
            assert chunk.metadata["has_overlap"] is True
            assert 1 <= chunk.metadata["overlap_elements"] <= 2


class TestApplyHeadings:
    def test_paragraph_inherits_heading_context(self):
        nodes = [heading("Chapter One", 1, children=[paragraph("Some body text.")])]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].text.startswith("H1: Chapter One\n---\n")
        assert "Some body text." in chunks[0].text
        assert chunks[0].metadata["headings"] == ["Chapter One"]

    def test_nested_headings_accumulate(self):
        nodes = [heading("Top", 1, children=[
            heading("Middle", 2, children=[paragraph("deep paragraph")]),
        ])]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert "H1: Top" in chunks[0].text
        assert "H2: Middle" in chunks[0].text
        assert chunks[0].metadata["headings"] == ["Top", "Middle"]

    def test_heading_deeper_than_previous_level_pads_gap(self):
        # Document starts directly with an H3: levels 1 and 2 are absent.
        nodes = [heading("Orphan Level Three", 3, children=[paragraph("gap paragraph")])]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].metadata["headings"] == ["", "", "Orphan Level Three"]
        # Empty gap headings must not render in the chunk text.
        assert "H1:" not in chunks[0].text
        assert "H2:" not in chunks[0].text
        assert "H3: Orphan Level Three" in chunks[0].text

    def test_h1_followed_by_h3_child_keeps_gap_slot(self):
        nodes = [heading("Root", 1, children=[
            heading("Skipped To Three", 3, children=[paragraph("content here")]),
        ])]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 1
        assert chunks[0].metadata["headings"] == ["Root", "", "Skipped To Three"]
        assert "H1: Root" in chunks[0].text
        assert "H3: Skipped To Three" in chunks[0].text

    def test_sibling_heading_replaces_previous_branch(self):
        nodes = [
            heading("First", 1, children=[paragraph("first body")]),
            heading("Second", 1, children=[paragraph("second body")]),
        ]
        chunks = make_chunker().apply(nodes, DOC_ID)

        assert len(chunks) == 2
        assert chunks[0].metadata["headings"] == ["First"]
        assert chunks[1].metadata["headings"] == ["Second"]
        assert "First" not in chunks[1].text


class TestStringification:
    """Covers _stringify_node_content branches not reachable from top level."""

    def test_table_node_inside_list_item_is_stringified(self):
        chunker = make_chunker()
        node = list_item("item with table", children=[
            {"type": "table", "content": "r1c1 | r1c2", "children": []},
        ])
        text = chunker._stringify_node_content(node)
        assert "item with table" in text
        assert "Table:" in text
        assert "r1c1 | r1c2" in text

    def test_heading_node_is_stringified_with_level_prefix(self):
        chunker = make_chunker()
        text = chunker._stringify_node_content(
            {"type": "heading", "level": 2, "content": "Inline Heading", "children": []}
        )
        assert text == "H2: Inline Heading"

    def test_unknown_node_type_stringifies_to_empty(self):
        chunker = make_chunker()
        assert chunker._stringify_node_content({"type": "mystery", "children": []}) == ""


class TestMetadataContract:
    def test_every_chunk_has_required_metadata_keys(self):
        nodes = [
            heading("Doc", 1, children=[
                paragraph("intro paragraph"),
                {
                    "type": "table",
                    "header": ["A"],
                    "data_rows": [["1"]],
                    "children": [],
                },
                {
                    "type": "list_container",
                    "level": 0,
                    "num_id": 1,
                    "children": [list_item("only item")],
                },
            ])
        ]
        chunks = make_chunker().apply(nodes, DOC_ID, source_format="docx")

        assert len(chunks) == 3
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            for key in ("document_id", "source_type", "node_type", "headings", "num_chars"):
                assert key in chunk.metadata, f"Missing metadata key: {key}"
            assert chunk.metadata["document_id"] == DOC_ID
            assert chunk.metadata["source_type"] == "docx"
            assert chunk.metadata["num_chars"] == len(chunk.text)

    def test_source_format_is_propagated(self):
        nodes = [paragraph("pdf-style paragraph")]
        chunks = make_chunker().apply(nodes, DOC_ID, source_format="pdf")
        assert chunks[0].metadata["source_type"] == "pdf"
