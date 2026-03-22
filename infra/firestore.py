# firestore.py
import os
from datetime import datetime, timezone

from fastapi import Request
from firebase_admin import firestore as firebase_firestore
from dotenv import load_dotenv
from typer.cli import app

load_dotenv()


def get_db(request: Request):
    """Return the Firestore client. Requires Firebase Admin SDK to be initialized first."""
    return request.app.state.db

def initialize_db():
    client = firebase_firestore.client()
    return client

# ── User ─────────────────────────────────────────────────────────────────────

def ensure_user_exists(db, user_id: str, email: str) -> None:
    """Create a user document if it doesn't already exist."""
    ref = db.collection("users").document(user_id)
    if not ref.get().exists:
        ref.set({"email": email, "created_at": datetime.now(timezone.utc)})


# ── Projects ──────────────────────────────────────────────────────────────────

def _project_ref(db, user_id: str, project_name: str):
    return db.collection("users").document(user_id).collection("projects").document(project_name)


def create_project(db, user_id: str, project_namespace: str, name: str) -> None:
    project_reference = _project_ref(db, user_id, name)
    if project_reference.get().exists:
        raise ValueError(f"Project '{name}' already exists")
    project_reference.set({
        "name": name,
        "namespace": project_namespace,
        "created_at": datetime.now(timezone.utc),
    })


def get_project(db, user_id: str, project_id: str) -> dict | None:
    doc = _project_ref(db, user_id, project_id).get()
    return doc.to_dict() if doc.exists else None


def project_name_exists(db, user_id: str, name: str) -> bool:
    docs = (
        db.collection("users").document(user_id).collection("projects")
        .where("name", "==", name)
        .limit(1)
        .stream()
    )
    return any(True for _ in docs)


def list_projects(db, user_id: str) -> list[dict]:
    docs = db.collection("users").document(user_id).collection("projects").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_project(db, user_id: str, project_id: str) -> None:
    """Delete all document subcollection entries, then the project document."""
    docs_ref = _project_ref(db, user_id, project_id).collection("documents")
    for doc in docs_ref.stream():
        doc.reference.delete()
    _project_ref(db, user_id, project_id).delete()


# ── Documents ─────────────────────────────────────────────────────────────────

def _document_ref(db, user_id: str, project_id: str, document_id: str):
    return _project_ref(db, user_id, project_id).collection("documents").document(document_id)


def create_document_meta(
    db,
    user_id: str,
    project_name: str,
    document_id: str,
    filename: str,
    chunks_indexed: int,
    authors: str = "Unknown",
    year: str = "Unknown",
) -> None:
    _document_ref(db, user_id, project_name, document_id).set({
        "filename": filename,
        "chunks_indexed": chunks_indexed,
        "authors": authors,
        "year": year,
        "created_at": datetime.now(timezone.utc),
    })


def get_document_meta(db, user_id: str, project_id: str, document_id: str) -> dict | None:
    doc = _document_ref(db, user_id, project_id, document_id).get()
    return doc.to_dict() if doc.exists else None


def list_documents(db, user_id: str, project_id: str) -> list[dict]:
    docs = _project_ref(db, user_id, project_id).collection("documents").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_document_meta(db, user_id: str, project_id: str, document_id: str) -> None:
    _document_ref(db, user_id, project_id, document_id).delete()
