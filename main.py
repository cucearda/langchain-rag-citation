# main.py
import tempfile
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from langchain_core.documents import Document
from pinecone import Pinecone

import firestore as fs
from auth import get_current_user, _ensure_firebase
from document_loading import parse_pdf_with_grobid, split_chunks
from firestore import get_db
from models import ProjectCreateRequest, CitationRequest
from vector_store import get_vector_store, INDEX_NAME, delete_document_chunks
from agents import invoke_retriever, invoke_citator, reconstruct_cited_paragraph


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_firebase()
    yield


app = FastAPI(lifespan=lifespan)


def delete_namespace(namespace: str) -> None:
    """Delete all vectors in a Pinecone namespace."""
    pc = Pinecone()
    index = pc.Index(INDEX_NAME)
    index.delete(delete_all=True, namespace=namespace)


# ── Projects ──────────────────────────────────────────────────────────────────

@app.post("/projects", status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    fs.ensure_user_exists(db, uid, user.get("email", ""))
    project_id = str(uuid.uuid4())
    fs.create_project(db, uid, project_id, body.name)
    project = fs.get_project(db, uid, project_id)
    return {"id": project_id, **project}


@app.get("/projects")
async def list_projects(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    fs.ensure_user_exists(db, uid, user.get("email", ""))
    return fs.list_projects(db, uid)


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_namespace(project["namespace"])
    fs.delete_project(db, uid, project_id)
    return Response(status_code=204)


# ── Documents ─────────────────────────────────────────────────────────────────

@app.post("/projects/{project_id}/documents", status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        docs = parse_pdf_with_grobid(tmp_path)
        chunks = split_chunks(docs)
        document_id = str(uuid.uuid4())

        vector_store = get_vector_store(namespace=project["namespace"])
        documents = []
        for chunk in chunks:
            chunk.metadata["doc_id"] = document_id
            documents.append(Document(page_content=chunk.text, metadata=chunk.metadata))

        vector_store.add_documents(documents)
    finally:
        os.unlink(tmp_path)

    fs.create_document_meta(db, uid, project_id, document_id, file.filename, len(documents))
    return {"id": document_id, "filename": file.filename, "chunks_indexed": len(documents)}


@app.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return fs.list_documents(db, uid, project_id)


@app.delete("/projects/{project_id}/documents/{document_id}", status_code=204)
async def delete_document(
    project_id: str,
    document_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    doc_meta = fs.get_document_meta(db, uid, project_id, document_id)
    if not doc_meta:
        raise HTTPException(status_code=404, detail="Document not found")

    pc = Pinecone()
    index = pc.Index(INDEX_NAME)
    delete_document_chunks(index, document_id)

    fs.delete_document_meta(db, uid, project_id, document_id)
    return Response(status_code=204)


# ── Citations ─────────────────────────────────────────────────────────────────

@app.post("/projects/{project_id}/citations")
async def get_citations(
    project_id: str,
    request: CitationRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    vector_store = get_vector_store(namespace=project["namespace"])

    try:
        retrieved_docs = invoke_retriever(request.paragraph, vector_store)
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
