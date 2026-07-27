"""Edge-case and robustness tests for the DocChunker facade, Chunk model and
utility helpers."""

import json
from pathlib import Path

import pytest

from docchunker import DocChunker
from docchunker.models.chunk import Chunk
from docchunker.processors.base_processor import BaseProcessor
from docchunker.utils.io_utils import write_json
from docchunker.utils.text_utils import (
    extract_keywords,
    get_file_extension,
    normalize_whitespace,
)

UNITTEST_DATA_DIR = Path(__file__).parent.parent / "data" / "unittests"


@pytest.fixture
def chunker():
    return DocChunker(chunk_size=1000)


class TestProcessDocumentErrors:
    def test_nonexistent_file_raises_file_not_found(self, chunker):
        with pytest.raises(FileNotFoundError, match="File not found"):
            chunker.process_document("/nonexistent/path/document.docx")

    def test_unsupported_extension_raises_value_error(self, chunker, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("plain text content")
        with pytest.raises(ValueError, match="Unsupported file format: txt"):
            chunker.process_document(str(txt_file))

    def test_extension_check_is_case_insensitive_for_missing_processor(self, chunker, tmp_path):
        weird_file = tmp_path / "archive.XYZ"
        weird_file.write_text("data")
        with pytest.raises(ValueError, match="Unsupported file format: xyz"):
            chunker.process_document(str(weird_file))

    def test_process_document_accepts_path_object(self, chunker):
        docx_file = UNITTEST_DATA_DIR / "sample_table.docx"
        if not docx_file.exists():
            pytest.skip(f"Test file not found: {docx_file}")
        chunks = chunker.process_document(docx_file)
        assert len(chunks) > 0


class TestProcessDocumentBytesErrors:
    def test_unsupported_format_raises_value_error(self, chunker):
        with pytest.raises(ValueError, match="Unsupported file format: html"):
            chunker.process_document_bytes(b"<html></html>", "html")

    def test_error_raised_before_touching_bytes(self, chunker):
        # Even empty bytes should fail on the format check first.
        with pytest.raises(ValueError, match="Unsupported file format"):
            chunker.process_document_bytes(b"", "epub")


class TestProcessDocuments:
    def test_empty_directory_returns_empty_list(self, chunker, tmp_path):
        assert chunker.process_documents(str(tmp_path), "*.docx") == []

    def test_non_matching_pattern_returns_empty_list(self, chunker):
        assert chunker.process_documents(str(UNITTEST_DATA_DIR), "*.nomatch") == []


class TestExportChunksToJson:
    def test_round_trip_preserves_text_and_metadata(self, chunker, tmp_path):
        chunks = [
            Chunk(text="first chunk", metadata={"node_type": "paragraph", "num_chars": 11}),
            Chunk(text="second chunk", metadata={"headings": ["H1", "H2"], "has_overlap": False}),
        ]
        output_file = tmp_path / "chunks.json"
        chunker.export_chunks_to_json(chunks, output_file)

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == [c.to_dict() for c in chunks]

    def test_round_trip_with_real_document(self, chunker, tmp_path):
        docx_file = UNITTEST_DATA_DIR / "nested_lists.docx"
        if not docx_file.exists():
            pytest.skip(f"Test file not found: {docx_file}")
        chunks = chunker.process_document(str(docx_file))
        output_file = tmp_path / "exported.json"
        chunker.export_chunks_to_json(chunks, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            loaded = json.load(f)

        assert len(loaded) == len(chunks)
        for original, restored in zip(chunks, loaded):
            assert restored["text"] == original.text
            assert restored["metadata"] == original.metadata

    def test_empty_chunk_list_exports_empty_array(self, chunker, tmp_path):
        output_file = tmp_path / "empty.json"
        chunker.export_chunks_to_json([], output_file)
        assert json.loads(output_file.read_text(encoding="utf-8")) == []


class TestChunkModel:
    def test_to_dict_contains_text_and_metadata(self):
        chunk = Chunk(text="hello", metadata={"node_type": "paragraph"})
        assert chunk.to_dict() == {"text": "hello", "metadata": {"node_type": "paragraph"}}

    def test_to_dict_is_json_serializable(self):
        chunk = Chunk(text="hello", metadata={"headings": ["A"], "num_chars": 5})
        assert json.loads(json.dumps(chunk.to_dict())) == chunk.to_dict()


class TestBaseProcessor:
    def test_process_raises_not_implemented(self):
        processor = BaseProcessor(chunk_size=100)
        with pytest.raises(NotImplementedError):
            processor.process("any_file.docx")

    def test_constructor_stores_configuration(self):
        processor = BaseProcessor(chunk_size=123, num_overlapping_elements=4)
        assert processor.chunk_size == 123
        assert processor.num_overlapping_elements == 4


class TestTextUtils:
    @pytest.mark.parametrize(
        "path, expected",
        [
            ("document.docx", "docx"),
            ("document.PDF", "pdf"),
            ("/tmp/some/path/report.Docx", "docx"),
            ("archive.tar.gz", "gz"),
            ("no_extension", ""),
            (Path("folder") / "file.pdf", "pdf"),
        ],
    )
    def test_get_file_extension(self, path, expected):
        assert get_file_extension(path) == expected

    def test_normalize_whitespace_collapses_runs(self):
        assert normalize_whitespace("hello    world") == "hello world"

    def test_normalize_whitespace_strips_ends(self):
        assert normalize_whitespace("  padded  ") == "padded"

    def test_normalize_whitespace_collapses_newlines(self):
        result = normalize_whitespace("line one\n\n\nline two")
        assert "line one" in result and "line two" in result
        assert "\n\n\n" not in result

    def test_extract_keywords_is_not_implemented(self):
        with pytest.raises(NotImplementedError):
            extract_keywords("some text")


class TestIoUtils:
    def test_write_json_dict_round_trip(self, tmp_path):
        target = tmp_path / "out.json"
        data = {"key": "value", "nested": {"a": 1}}
        write_json(str(target), data)
        assert json.loads(target.read_text()) == data

    def test_write_json_list_round_trip(self, tmp_path):
        target = tmp_path / "out.json"
        data = [{"a": 1}, {"b": 2}]
        write_json(str(target), data)
        assert json.loads(target.read_text()) == data


class TestChunkerConfiguration:
    def test_chunk_size_propagates_to_processors(self):
        chunker = DocChunker(chunk_size=555, num_overlapping_elements=3)
        for name in ("docx", "pdf"):
            assert chunker.processors[name].chunk_size == 555
            assert chunker.processors[name].num_overlapping_elements == 3
            assert chunker.processors[name].chunker.chunk_size == 555
            assert chunker.processors[name].chunker.num_overlapping_elements == 3

    def test_supported_formats_registered(self):
        chunker = DocChunker()
        assert set(chunker.processors) == {"docx", "pdf"}
