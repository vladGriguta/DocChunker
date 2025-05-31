"""
Defines the Chunk class for representing document fragments.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any]