import os

from langchain_community.document_loaders.parsers import GrobidParser
from langchain_community.document_loaders.generic import GenericLoader
from langchain_text_splitters import CharacterTextSplitter
from models import Chunk

def parse_pdf_with_grobid(file_path: str) -> list:
    directory = os.path.dirname(file_path) or "."
    filename = os.path.basename(file_path)
    loader = GenericLoader.from_filesystem(
        directory,
        glob=filename,
        suffixes=[".pdf"],
        parser=GrobidParser(segment_sentences=False),
    )
    docs = []
    try:
        docs = loader.load()
    except Exception as e:
        print(f"Error: {e}")
    return docs

def split_chunks(docs: dict) -> list:
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