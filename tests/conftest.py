import pytest
from pathlib import Path

@pytest.fixture
def sample_docx_path():
    return Path(__file__).parent.parent / "data" / "samples" / "complex_document.docx"
