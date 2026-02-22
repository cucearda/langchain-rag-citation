from dataclasses import dataclass
from typing import List

@dataclass
class Chunk:
    """Represents a text chunk extracted from a PDF."""
    text: str
    paragraph: int
    pages: List[int]
    section_title: str
    section_number: str
    paper_title: str

@dataclass
class Embedding:
    chunk: Chunk
    embedding: List[float]

