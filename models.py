from typing import Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str
    metadata: dict


class CitationSource(BaseModel):
    """Metadata of the cited document."""
    paper_title: str = Field(description="Title of the cited paper")
    authors: str = Field(description="Authors of the paper, comma-separated")
    year: str = Field(description="Publication year")
    section_title: str = Field(description="Section title where the cited text comes from")
    section_number: Optional[str] = Field(default=None, description="Section number if available")
    pages: Optional[str] = Field(default=None, description="Page numbers if available")


class Citation(BaseModel):
    """A single citation for a specific span of text in the paragraph."""
    start: int = Field(description="Character offset (0-indexed) in the original paragraph where the cited claim begins")
    end: int = Field(description="Character offset (0-indexed, exclusive) in the original paragraph where the cited claim ends")
    reason: str = Field(description="Why this source was chosen to support this specific claim")
    source: CitationSource = Field(description="Metadata of the cited document")
    relevant_quote: str = Field(description="Verbatim excerpt from the source document that supports the claim")
    relevance_explanation: str = Field(description="Explanation of how this quote supports the claim in the paragraph")


class CitatorResult(BaseModel):
    """Structured output of the citator agent."""
    citations: list[Citation] = Field(description="All citations found for the paragraph, one per supported claim")
