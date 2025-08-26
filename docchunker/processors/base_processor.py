
from typing import Union, BinaryIO
from docchunker.models.chunk import Chunk


class BaseProcessor:
    """
    Base class for document processors.
    """

    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements

    def process(self, file_input: Union[str, BinaryIO]) -> list[Chunk]:
        """Process the document and return chunks.
        
        Args:
            file_input: Either a file path (str) or a file-like object (BinaryIO)
        """
        raise NotImplementedError("Subclasses must implement this method.")
