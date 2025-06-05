
from docchunker.models.chunk import Chunk


class BaseProcessor:
    """
    Base class for document processors.
    """

    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements

    def process(self, file_path: str) -> list[Chunk]:
        """Process the document and return chunks."""
        raise NotImplementedError("Subclasses must implement this method.")
