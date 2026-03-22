import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pinecone import Pinecone

logger = logging.getLogger(__name__)

import infra.firestore as fs
from infra.auth import get_current_user
from infra.firestore import get_db
from models import ProjectCreateRequest
from infra.vector_store import INDEX_NAME

router = APIRouter(prefix="/projects", tags=["projects"])


def delete_namespace(namespace: str) -> None:
    """Delete all vectors in a Pinecone namespace."""
    pc = Pinecone()
    index = pc.Index(INDEX_NAME)
    index.delete(delete_all=True, namespace=namespace)


@router.post("", status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    fs.ensure_user_exists(db, uid)
    project_namespace = str(uuid.uuid4())
    try:
        fs.create_project(db, uid, project_namespace, body.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f": {e}")

    project = fs.get_project(db, uid, body.name)
    return {**project}


@router.get("")
async def list_projects(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    fs.ensure_user_exists(db, uid)
    return fs.list_projects(db, uid)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    uid = user["uid"]
    project = fs.get_project(db, uid, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        delete_namespace(project["namespace"])
    except Exception as e:
        logger.error("Failed to delete Pinecone namespace %s: %s", project["namespace"], e)

    try:
        fs.delete_project(db, uid, project_id)
    except Exception as e:
        raise HTTPException(status_code=e.status, details="Failed to delete fs project")

    return Response(status_code=204)
