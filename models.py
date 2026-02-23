from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str
    metadata: dict


class DocumentRecord(BaseModel):
    doc_id: str
    filename: str
    paper_title: str
    authors: str
    year: str
    chunks_indexed: int
    uploaded_at: datetime


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    paper_title: str
    authors: str
    year: str
    chunks_indexed: int
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentDeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


class ChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    paper_title: str
    authors: str
    year: str
    section_title: str
    section_number: Optional[str]
    pages: Optional[str]
    text: str


class ChunkListResponse(BaseModel):
    doc_id: str
    chunks: list[ChunkResponse]
    total: int


class CitationRequest(BaseModel):
    paragraph: str = Field(..., min_length=1, max_length=10_000)


class CitationRecord(BaseModel):
    citation_id: str
    original_paragraph: str
    cited_paragraph: str
    created_at: datetime


class CitationResponse(BaseModel):
    citation_id: str
    original_paragraph: str
    cited_paragraph: str
    created_at: datetime
