import sys

from langchain_core.documents import Document

from document_loading import parse_pdf_with_grobid, split_chunks
from vector_store import get_vector_store, get_retriever



if __name__ == "__main__":
    return "Hello, World!"