import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from langchain_core.documents import Document

from document_loading import parse_pdf_with_grobid, split_chunks
from models import (
    ChunkListResponse,
    ChunkResponse,
    CitationRecord,
    CitationRequest,
    CitationResponse,
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentResponse,
)
from vector_store import delete_document_chunks, get_vector_store, list_document_chunks
from agents import document_retriever_agent, invoke_citator

app = FastAPI()
vector_store = get_vector_store()

documents_store: dict[str, DocumentRecord] = {}
citations_store: dict[str, CitationRecord] = {}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        docs = parse_pdf_with_grobid(tmp_path)
        chunks = split_chunks(docs)

        doc_id = str(uuid.uuid4())
        for chunk in chunks:
            chunk.metadata["doc_id"] = doc_id

        documents = [
            Document(page_content=chunk.text, metadata=chunk.metadata)
            for chunk in chunks
        ]
        vector_store.add_documents(documents)
    finally:
        os.unlink(tmp_path)

    first_meta = chunks[0].metadata if chunks else {}
    record = DocumentRecord(
        doc_id=doc_id,
        filename=file.filename or "",
        paper_title=first_meta.get("paper_title", "Unknown"),
        authors=first_meta.get("authors", "Unknown"),
        year=first_meta.get("year", "Unknown"),
        chunks_indexed=len(documents),
        uploaded_at=datetime.now(timezone.utc),
    )
    documents_store[doc_id] = record
    return DocumentResponse(**record.model_dump())


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    docs = [DocumentResponse(**r.model_dump()) for r in documents_store.values()]
    return DocumentListResponse(documents=docs, total=len(docs))


@app.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    record = documents_store.get(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**record.model_dump())


@app.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str):
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    deleted = delete_document_chunks(vector_store._index, doc_id)
    documents_store.pop(doc_id)
    return DocumentDeleteResponse(doc_id=doc_id, deleted_chunks=deleted)


@app.get("/documents/{doc_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(doc_id: str):
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    matches = list_document_chunks(vector_store._index, doc_id)
    chunk_responses = []
    for match in matches:
        meta = match.get("metadata", {})
        chunk_responses.append(
            ChunkResponse(
                chunk_id=match["id"],
                doc_id=meta.get("doc_id", doc_id),
                paper_title=meta.get("paper_title", ""),
                authors=meta.get("authors", ""),
                year=meta.get("year", ""),
                section_title=meta.get("section_title", ""),
                section_number=meta.get("section_number"),
                pages=meta.get("pages"),
                text=meta.get("text", ""),
            )
        )
    return ChunkListResponse(doc_id=doc_id, chunks=chunk_responses, total=len(chunk_responses))


@app.post("/citations", response_model=CitationResponse, status_code=201)
async def create_citation(request: CitationRequest):
    retriever_result = document_retriever_agent.invoke(
        {"messages": [{"role": "user", "content": request.paragraph}]}
    )

    retrieved_docs = []
    for msg in retriever_result["messages"]:
        if hasattr(msg, "artifact") and msg.artifact:
            retrieved_docs.extend(msg.artifact)

    citator_result = invoke_citator(retrieved_docs, request.paragraph)
    cited_paragraph = citator_result["messages"][-1].content

    citation_id = str(uuid.uuid4())
    record = CitationRecord(
        citation_id=citation_id,
        original_paragraph=request.paragraph,
        cited_paragraph=cited_paragraph,
        created_at=datetime.now(timezone.utc),
    )
    citations_store[citation_id] = record
    return CitationResponse(**record.model_dump())


@app.get("/citations/{citation_id}", response_model=CitationResponse)
async def get_citation(citation_id: str):
    record = citations_store.get(citation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Citation not found")
    return CitationResponse(**record.model_dump())
