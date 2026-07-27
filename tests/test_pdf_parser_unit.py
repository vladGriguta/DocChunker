"""Unit tests for PdfParser internals and its PyPDF fallback path.

The PyMuPDF path is exercised by the YAML-driven PDF tests; here we cover the
pure-heuristic helpers with synthetic inputs and force the PyPDF fallback on a
real fixture so both extraction backends stay tested.
"""

from io import BytesIO
from pathlib import Path

import pytest

from docchunker import DocChunker
from docchunker.processors.pdf_parser import PdfParser

UNITTEST_DATA_DIR = Path(__file__).parent.parent / "data" / "unittests"
SAMPLE_PDF = UNITTEST_DATA_DIR / "sample_table.pdf"
NESTED_LISTS_PDF = UNITTEST_DATA_DIR / "nested_lists.pdf"

VALID_NODE_TYPES = {"heading", "paragraph", "list_item", "list_container", "table"}


@pytest.fixture
def parser():
    return PdfParser()


class TestPypdfFallback:
    def test_fallback_parses_real_pdf_from_path(self, parser):
        if not SAMPLE_PDF.exists():
            pytest.skip(f"Test file not found: {SAMPLE_PDF}")
        parser.use_pymupdf = False
        elements = parser.apply(str(SAMPLE_PDF))

        assert isinstance(elements, list)
        assert len(elements) > 0
        for element in elements:
            assert element["type"] in VALID_NODE_TYPES

    def test_fallback_parses_pdf_from_bytesio(self, parser):
        if not NESTED_LISTS_PDF.exists():
            pytest.skip(f"Test file not found: {NESTED_LISTS_PDF}")
        parser.use_pymupdf = False
        with open(NESTED_LISTS_PDF, "rb") as f:
            elements = parser.apply(BytesIO(f.read()))

        assert isinstance(elements, list)
        assert len(elements) > 0

    def test_full_pipeline_with_fallback_produces_chunks(self):
        if not NESTED_LISTS_PDF.exists():
            pytest.skip(f"Test file not found: {NESTED_LISTS_PDF}")
        chunker = DocChunker(chunk_size=1000)
        chunker.processors["pdf"].parser.use_pymupdf = False
        chunks = chunker.process_document(str(NESTED_LISTS_PDF))

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["source_type"] == "pdf"
            assert chunk.text.strip()


class TestDetectListItem:
    @pytest.mark.parametrize("text", ["- bullet dash", "• bullet dot", "* bullet star"])
    def test_bullet_markers_detected(self, parser, text):
        result = parser._detect_list_item(text)
        assert result is not None
        assert result["num_id"] == -1
        assert result["level"] == 0
        assert "bullet" in result["content"]

    @pytest.mark.parametrize("text, content", [
        ("1. first numbered", "first numbered"),
        ("2) second numbered", "second numbered"),
        ("(3) third numbered", "third numbered"),
        ("a. lettered item", "lettered item"),
        ("iv. roman item", "roman item"),
    ])
    def test_numbered_markers_detected(self, parser, text, content):
        result = parser._detect_list_item(text)
        assert result is not None
        assert result["num_id"] == 1
        assert result["content"] == content

    def test_indentation_maps_to_level(self, parser):
        result = parser._detect_list_item("        - deeply indented bullet")
        assert result is not None
        assert result["level"] == 2  # 8 spaces // 4 per level

    @pytest.mark.parametrize("text", [
        "Plain sentence with no marker.",
        "",
        "100 items were sold",  # digits without dot-space marker
    ])
    def test_non_list_text_returns_none(self, parser, text):
        assert parser._detect_list_item(text) is None


class TestDetectListItemAdvanced:
    def test_x_position_can_deepen_level(self, parser):
        # 80 points / 36 per indent => position level 2 beats text level 0.
        result = parser._detect_list_item_advanced("- positioned bullet", {"x": 80})
        assert result is not None
        assert result["level"] == 2

    def test_non_list_stays_none_regardless_of_position(self, parser):
        assert parser._detect_list_item_advanced("Just a paragraph.", {"x": 200}) is None


class TestTableRowDetection:
    def test_multi_column_text_detected(self, parser):
        assert parser._is_table_row("Name    Age    City") is True

    def test_tab_separated_text_detected(self, parser):
        assert parser._is_table_row("Name\tAge\tCity") is True

    def test_regular_sentence_not_detected(self, parser):
        assert parser._is_table_row("This is a normal sentence.") is False


class TestLinesLikelyConnected:
    def test_empty_lines_break_paragraphs(self, parser):
        assert parser._lines_likely_connected("", "next line") is False
        assert parser._lines_likely_connected("prev line", "") is False

    def test_sentence_end_breaks_unless_lowercase_continuation(self, parser):
        assert parser._lines_likely_connected("This ends a sentence.", "New Topic Header") is False
        assert parser._lines_likely_connected(
            "This ends a sentence.", "but the following text continues in lowercase for a while"
        ) is True

    def test_trailing_comma_continues(self, parser):
        assert parser._lines_likely_connected("first item,", "second item") is True

    def test_no_punctuation_continues(self, parser):
        assert parser._lines_likely_connected("line without punctuation", "More text") is True


class TestFontStatistics:
    def test_empty_blocks_return_defaults(self, parser):
        stats = parser._calculate_font_statistics([])
        assert stats["avg_size"] == 12
        assert stats["std_size"] == 0

    def test_single_block_has_zero_std(self, parser):
        stats = parser._calculate_font_statistics([{"font_size": 14}])
        assert stats["avg_size"] == 14
        assert stats["std_size"] == 0

    def test_multiple_blocks_compute_min_max(self, parser):
        blocks = [{"font_size": s} for s in (10, 12, 20)]
        stats = parser._calculate_font_statistics(blocks)
        assert stats["min_size"] == 10
        assert stats["max_size"] == 20
        assert stats["avg_size"] == pytest.approx(14)


class TestHeadingHeuristics:
    @pytest.mark.parametrize("ratio_size, expected_level", [
        (24, 1),   # ratio 2.0
        (20, 2),   # ratio ~1.67
        (17, 3),   # ratio ~1.42
        (15, 4),   # ratio 1.25
        (12, 5),   # ratio 1.0
    ])
    def test_determine_heading_level_from_font_ratio(self, parser, ratio_size, expected_level):
        assert parser._determine_heading_level(ratio_size, 12.0) == expected_level

    def test_large_bold_short_text_is_heading(self, parser):
        block = {"text": "Chapter Overview", "font_size": 20, "is_bold": True}
        stats = {"avg_size": 12}
        assert parser._is_heading_with_formatting(block, stats) is True

    def test_normal_sentence_is_not_heading(self, parser):
        block = {
            "text": "this is an ordinary sentence that ends with a period and keeps going for quite a while"
                    " so that it does not look like a short title at all, which matters here.",
            "font_size": 12,
            "is_bold": False,
        }
        stats = {"avg_size": 12}
        assert parser._is_heading_with_formatting(block, stats) is False


class TestFallbackHeuristics:
    def test_estimate_font_size_branches(self, parser):
        assert parser._estimate_font_size("ALL CAPS HEADING") == 16
        assert parser._estimate_font_size("Section heading:") == 14
        assert parser._estimate_font_size("Short line no period") == 13
        assert parser._estimate_font_size(
            "A long ordinary paragraph line that definitely ends with a period and provides detail."
        ) == 12

    @pytest.mark.parametrize("text, expected", [
        ("INTRODUCTION", True),
        ("Setup instructions:", True),
        ("1.2 Architecture", True),
        ("Chapter 5 begins here", True),
        ("just a lowercase continuation of an earlier sentence without markers", False),
    ])
    def test_looks_like_new_section(self, parser, text, expected):
        assert parser._looks_like_new_section(text) is expected


class TestProcessTextBlock:
    def test_empty_text_returns_none(self, parser):
        assert parser._process_text_block({"text": "   ", "font_size": 12}, 12.0) is None

    def test_large_font_becomes_heading(self, parser):
        element = parser._process_text_block({"text": "Big Title", "font_size": 24}, 12.0)
        assert element is not None
        assert element["type"] == "heading"
        assert element["level"] == 1

    def test_list_marker_becomes_list_item(self, parser):
        element = parser._process_text_block({"text": "- bullet content", "font_size": 12}, 12.0)
        assert element is not None
        assert element["type"] == "list_item"
        assert element["content"] == "bullet content"

    def test_plain_text_becomes_paragraph(self, parser):
        element = parser._process_text_block(
            {"text": "An ordinary paragraph of body text that describes something mundane.",
             "font_size": 12},
            12.0,
        )
        assert element is not None
        assert element["type"] == "paragraph"
