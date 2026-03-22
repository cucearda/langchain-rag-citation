from fastapi import APIRouter, Depends, HTTPException, Request

import infra.firestore as fs
from services.agents import invoke_citator, invoke_retriever, reconstruct_cited_paragraph
from infra.auth import get_current_user
from infra.firestore import get_db
from models import CitationRequest
from infra.vector_store import get_vector_store_by_namespace

router = APIRouter(prefix="/projects", tags=["citations"])


@router.post("/{project_id}/citations")
async def get_citations(
    project_id: str,
    requestBody: CitationRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    vector_store = get_vector_store_by_namespace(namespace=project["namespace"], embeddings=request.app.state.embeddings, index=request.app.state.vector_store_index)

    try:
        retrieved_docs = await invoke_retriever(requestBody.paragraph, vector_store)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retriever agent failed: {e}")

    try:
        citation_list = await invoke_citator(retrieved_docs, request.paragraph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citator agent failed: {e}")

    return {
        "citations": [c.model_dump() for c in citation_list],
        "cited_paragraph": reconstruct_cited_paragraph(request.paragraph, citation_list),
    }
