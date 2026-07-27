"""
Tests for chunk size homogenization in DocumentChunker.

These tests feed synthetic hierarchical node lists directly to
DocumentChunker.apply() to verify:
- Oversized paragraphs are split at sentence boundaries (with heading context).
- Consecutive small paragraphs under the same heading context are merged.
- Table and list container behavior is unchanged.
- Boundary conditions (paragraph exactly at chunk_size, single tiny paragraph).
"""

from docchunker.processors.document_chunker import DocumentChunker


def make_paragraph(content: str) -> dict:
    return {"type": "paragraph", "content": content}


def make_heading(content: str, level: int = 1, children: list | None = None) -> dict:
    return {"type": "heading", "content": content, "level": level, "children": children or []}


class TestOversizedParagraphSplitting:
    def test_oversized_paragraph_is_split_at_sentence_boundaries(self):
        chunker = DocumentChunker(chunk_size=200)
        sentences = [f"This is sentence number {i} with some padding words." for i in range(12)]
        long_paragraph = " ".join(sentences)
        assert len(long_paragraph) > 200

        nodes = [make_heading("Intro", 1, [make_paragraph(long_paragraph)])]
        chunks = chunker.apply(nodes, "doc1")

        assert len(chunks) > 1, "Oversized paragraph should be split into multiple chunks"
        for chunk in chunks:
            assert len(chunk.text) <= 200, f"Chunk exceeds chunk_size: {len(chunk.text)} chars"
            assert chunk.metadata["node_type"] == "paragraph"
            assert chunk.metadata["is_split"] is True
            assert chunk.metadata["split_total"] == len(chunks)
            assert chunk.metadata["headings"] == ["Intro"]
            assert chunk.text.startswith("H1: Intro\n---\n"), "Each split chunk must carry the heading prefix"
            assert chunk.metadata["num_chars"] == len(chunk.text)

        assert [c.metadata["split_index"] for c in chunks] == list(range(len(chunks)))

        # No sentence content is lost.
        reconstructed = " ".join(c.text.split("---\n", 1)[1] for c in chunks)
        assert reconstructed == long_paragraph

    def test_split_pieces_end_at_sentence_boundaries(self):
        chunker = DocumentChunker(chunk_size=200)
        sentences = [f"Sentence {i} is here." for i in range(30)]
        nodes = [make_paragraph(" ".join(sentences))]
        chunks = chunker.apply(nodes, "doc1")

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.text.rstrip().endswith("."), "Split pieces should end at a sentence boundary"

    def test_single_overlong_sentence_falls_back_to_hard_split(self):
        chunker = DocumentChunker(chunk_size=100)
        giant_sentence = "x" * 350  # no sentence boundaries at all
        chunks = chunker.apply([make_paragraph(giant_sentence)], "doc1")

        assert len(chunks) == 4  # 350 chars / 100 available
        for chunk in chunks:
            assert len(chunk.text) <= 100
            assert chunk.metadata["is_split"] is True
        assert "".join(c.text for c in chunks) == giant_sentence

    def test_paragraph_exactly_at_chunk_size_is_not_split(self):
        chunker = DocumentChunker(chunk_size=100)
        content = "a" * 100  # headings empty, so full chunk_size is available
        chunks = chunker.apply([make_paragraph(content)], "doc1")

        assert len(chunks) == 1
        assert chunks[0].text == content
        assert chunks[0].metadata["node_type"] == "paragraph"
        assert "is_split" not in chunks[0].metadata

    def test_split_accounts_for_heading_prefix_length(self):
        chunker = DocumentChunker(chunk_size=120)
        heading = "A fairly descriptive section heading"
        content = ". ".join(["Some words here"] * 10) + "."
        nodes = [make_heading(heading, 1, [make_paragraph(content)])]
        chunks = chunker.apply(nodes, "doc1")

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.text) <= 120, "Heading prefix must be counted against chunk_size"


class TestUndersizedParagraphMerging:
    def test_consecutive_tiny_paragraphs_are_merged(self):
        chunker = DocumentChunker(chunk_size=1000)  # min_chunk_size defaults to 250
        tiny_paragraphs = [f"Tiny paragraph {i}." for i in range(10)]
        nodes = [make_heading("Section", 1, [make_paragraph(p) for p in tiny_paragraphs])]
        chunks = chunker.apply(nodes, "doc1")

        assert len(chunks) < 10, "Tiny paragraphs should be merged into fewer chunks"
        merged = [c for c in chunks if c.metadata["node_type"] == "paragraph_group"]
        assert merged, "Expected at least one merged paragraph_group chunk"
        for chunk in merged:
            assert chunk.metadata["num_merged_elements"] > 1
            assert chunk.metadata["headings"] == ["Section"]
            assert chunk.metadata["num_chars"] == len(chunk.text)
            assert chunk.text.count("H1: Section") == 1, "Heading prefix must not be duplicated when merging"
        total_merged = sum(c.metadata.get("num_merged_elements", 1) for c in chunks)
        assert total_merged == 10, "No paragraph should be lost or duplicated"

    def test_merged_chunks_stay_within_chunk_size(self):
        chunker = DocumentChunker(chunk_size=300)
        paragraphs = [f"Paragraph number {i} with a moderate amount of content in it." for i in range(20)]
        nodes = [make_heading("Section", 1, [make_paragraph(p) for p in paragraphs])]
        chunks = chunker.apply(nodes, "doc1")

        for chunk in chunks:
            assert len(chunk.text) <= 300

    def test_paragraphs_under_different_headings_are_not_merged(self):
        chunker = DocumentChunker(chunk_size=1000)
        nodes = [
            make_heading("Section A", 1, [make_paragraph("Short one.")]),
            make_heading("Section B", 1, [make_paragraph("Short two.")]),
        ]
        chunks = chunker.apply(nodes, "doc1")

        assert len(chunks) == 2, "Paragraphs under different headings must not be merged"
        assert chunks[0].metadata["headings"] == ["Section A"]
        assert chunks[1].metadata["headings"] == ["Section B"]
        assert all(c.metadata["node_type"] == "paragraph" for c in chunks)

    def test_single_tiny_paragraph_stays_plain_paragraph(self):
        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.apply([make_heading("Section", 1, [make_paragraph("Just one tiny paragraph.")])], "doc1")

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "paragraph"
        assert "num_merged_elements" not in chunks[0].metadata
        assert "is_split" not in chunks[0].metadata

    def test_non_paragraph_node_breaks_merge_run(self):
        chunker = DocumentChunker(chunk_size=1000)
        list_container = {
            "type": "list_container",
            "children": [{"type": "list_item", "content": "An item", "level": 0, "num_id": -1}],
        }
        nodes = [
            make_heading("Section", 1, [
                make_paragraph("Before the list."),
                list_container,
                make_paragraph("After the list."),
            ])
        ]
        chunks = chunker.apply(nodes, "doc1")

        node_types = [c.metadata["node_type"] for c in chunks]
        assert node_types == ["paragraph", "list_container", "paragraph"], \
            "Paragraphs separated by another element must not be merged across it"

    def test_custom_min_chunk_size_controls_merging(self):
        # min_chunk_size=1 effectively disables merging.
        chunker = DocumentChunker(chunk_size=1000, min_chunk_size=1)
        paragraphs = [f"Tiny {i}." for i in range(5)]
        chunks = chunker.apply([make_paragraph(p) for p in paragraphs], "doc1")
        assert len(chunks) == 5
        assert all(c.metadata["node_type"] == "paragraph" for c in chunks)


class TestExistingBehaviorUnchanged:
    def test_table_chunking_unchanged(self):
        chunker = DocumentChunker(chunk_size=1000)
        table = {
            "type": "table",
            "header": ["Name", "Value"],
            "data_rows": [["alpha", "1"], ["beta", "2"]],
        }
        chunks = chunker.apply([make_heading("Data", 1, [table])], "doc1")

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "table_rows"
        assert "Name: alpha | Value: 1" in chunks[0].text
        assert "is_split" not in chunks[0].metadata
        assert "num_merged_elements" not in chunks[0].metadata

    def test_list_container_chunking_unchanged(self):
        chunker = DocumentChunker(chunk_size=1000)
        list_container = {
            "type": "list_container",
            "children": [
                {"type": "list_item", "content": f"Item {i}", "level": 0, "num_id": -1}
                for i in range(3)
            ],
        }
        chunks = chunker.apply([make_heading("Lists", 1, [list_container])], "doc1")

        assert len(chunks) == 1
        assert chunks[0].metadata["node_type"] == "list_container"
        assert "- Item 0" in chunks[0].text

    def test_empty_paragraphs_are_skipped(self):
        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.apply([make_paragraph("   "), make_paragraph("")], "doc1")
        assert chunks == []
