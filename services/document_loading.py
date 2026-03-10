import os

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders.parsers import GrobidParser
from langchain_text_splitters import CharacterTextSplitter
from models import Chunk

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"


def _extract_header_metadata(soup: BeautifulSoup) -> dict:
    """Extract authors and year from the TEI header."""
    metadata = {}

    # Extract authors
    header = soup.find("teiHeader")
    if header:
        authors = []
        for author in header.find_all("author"):
            persname = author.find("persName")
            if persname:
                forename = persname.find("forename")
                surname = persname.find("surname")
                name_parts = []
                if forename:
                    name_parts.append(forename.text.strip())
                if surname:
                    name_parts.append(surname.text.strip())
                if name_parts:
                    authors.append(" ".join(name_parts))
        metadata["authors"] = ", ".join(authors) if authors else "Unknown"

        # Extract year
        date_tag = header.find("date", {"type": "published"})
        if date_tag and date_tag.get("when"):
            metadata["year"] = date_tag["when"][:4]
        else:
            metadata["year"] = "Unknown"

    return metadata


def parse_pdf_with_grobid(file_path: str, grobid_url: str = GROBID_URL) -> list:
    """Parse a PDF with Grobid, extracting body chunks plus authors/year from the header."""
    with open(file_path, "rb") as pdf:
        files = {"input": (file_path, pdf, "application/pdf", {"Expires": "0"})}
        data = {
            "generateIDs": "1",
            "consolidateHeader": "1",
            "segmentSentences": "1",
            "teiCoordinates": ["head", "s"],
        }
        r = requests.post(grobid_url, files=files, data=data, timeout=60)

    xml_data = r.text
    soup = BeautifulSoup(xml_data, "xml")
    header_meta = _extract_header_metadata(soup)

    # Use the existing GrobidParser to process body sections
    parser = GrobidParser(segment_sentences=False, grobid_server=grobid_url)
    docs = list(parser.process_xml(file_path, xml_data, segment_sentences=False))

    # Inject authors and year into each document's metadata
    for doc in docs:
        doc.metadata["authors"] = header_meta.get("authors", "Unknown")
        doc.metadata["year"] = header_meta.get("year", "Unknown")

    return docs


def split_chunks(docs: list) -> list:
    chunks: list[Chunk] = []
    for doc in docs:
        text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base", chunk_size=1500, chunk_overlap=300
        )
        texts = text_splitter.split_text(doc.page_content)
        for i, text in enumerate(texts):
            chunk = Chunk(
                text=text,
                metadata=doc.metadata
            )
            chunks.append(chunk)
    return chunks
