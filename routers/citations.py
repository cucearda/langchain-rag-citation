from fastapi import APIRouter, Depends, HTTPException

import firestore as fs
from agents import invoke_citator, invoke_retriever, reconstruct_cited_paragraph
from auth import get_current_user
from firestore import get_db
from models import CitationRequest
from vector_store import get_vector_store

router = APIRouter(prefix="/projects", tags=["citations"])


@router.post("/{project_id}/citations")
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
