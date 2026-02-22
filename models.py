from dataclasses import dataclass
from typing import List

@dataclass
class Chunk:
    """Represents a text chunk extracted from a PDF."""
    text: str
    metadata: dict

@dataclass
class Embedding:
    chunk: Chunk
    embedding: List[float]

@dataclass
class RetrievedDocumentsForClaim:
    DocumentForClaim: List[DocumentForClaim]

@dataclass
class DocumentForClaim:
    claim: str
    title: str
