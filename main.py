import sys

from langchain_core.documents import Document

from document_loading import parse_pdf_with_grobid, split_chunks
from vector_store import get_vector_store, get_retriever



if __name__ == "__main__":
    docs = parse_pdf_with_grobid("./")
    chunks = split_chunks(docs)

    documents = [
        Document(page_content=chunk.text, metadata=chunk.metadata)
        for chunk in chunks
    ]

    vector_store = get_vector_store()
    vector_store.add_documents(documents)

    retriever = get_retriever(vector_store)
    print(retriever.get_relevant_documents("Hope is the emotion that drives the teams, and makes them decide if they will quit or not quit"))