from docchunker import DocChunker

def test_docx_processing(sample_docx_path):
    chunker = DocChunker()
    chunks = chunker.process_document(str(sample_docx_path))
    assert isinstance(chunks, list)
    assert len(chunks) > 0
