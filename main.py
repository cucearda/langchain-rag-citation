import tempfile
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from langchain_core.documents import Document

from document_loading import parse_pdf_with_grobid, split_chunks
from vector_store import get_vector_store
from agents import invoke_retriever, invoke_citator, reconstruct_cited_paragraph

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
async def citations(request: CitationRequest):
    try:
        retrieved_docs = invoke_retriever(request.paragraph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retriever agent failed: {e}")

    try:
        citation_list = invoke_citator(retrieved_docs, request.paragraph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citator agent failed: {e}")

    return {
        "citations": [c.model_dump() for c in citation_list],
        "cited_paragraph": reconstruct_cited_paragraph(request.paragraph, citation_list),
    }