import tempfile
import os

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from langchain_core.documents import Document

from document_loading import parse_pdf_with_grobid, split_chunks
from vector_store import get_vector_store
from agents import document_retriever_agent, invoke_citator

app = FastAPI()
vector_store = get_vector_store()


class CitationRequest(BaseModel):
    paragraph: str


@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        docs = parse_pdf_with_grobid(tmp_path)
        chunks = split_chunks(docs)

        documents = []
        for chunk in chunks:
            documents.append(
                Document(page_content=chunk.text, metadata=chunk.metadata)
            )

        vector_store.add_documents(documents)
    finally:
        os.unlink(tmp_path)

    return {"status": "success", "chunks_indexed": len(documents)}


@app.post("/get-citations")
async def get_citations(request: CitationRequest):
    retriever_result = document_retriever_agent.invoke(
        {"messages": [{"role": "user", "content": request.paragraph}]}
    )

    retrieved_docs = []
    for msg in retriever_result["messages"]:
        if hasattr(msg, "artifact") and msg.artifact:
            retrieved_docs.extend(msg.artifact)

    citator_result = invoke_citator(retrieved_docs, request.paragraph)

    cited_paragraph = citator_result["messages"][-1].content

    return {"cited_paragraph": cited_paragraph}
