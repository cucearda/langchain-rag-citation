import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from langchain_core.documents import Document
from pinecone import Pinecone

import infra.firestore as fs
from infra.auth import get_current_user
from services.document_loading import parse_pdf_with_grobid, split_chunks
from infra.firestore import get_db
from infra.vector_store import INDEX_NAME, delete_document_chunks, get_vector_store

router = APIRouter(prefix="/projects", tags=["documents"])


@router.post("/{project_name}/documents", status_code=201)
async def upload_document(
    project_name: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_name)
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

    # Meta data of the first chunk is same as rest of the documents
    first_meta = chunks[0].metadata if chunks else {}
    fs.create_document_meta(
        db, uid, project_name, document_id, file.filename, len(documents),
        authors=first_meta.get("authors", "Unknown"),
        year=first_meta.get("year", "Unknown"),
    )
    return {"id": document_id, "filename": file.filename, "chunks_indexed": len(documents)}


@router.get("/{project_id}/documents")
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


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
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
