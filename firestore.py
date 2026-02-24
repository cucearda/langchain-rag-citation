# firestore.py
import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import firestore as firebase_firestore
from dotenv import load_dotenv

load_dotenv()


def get_db():
    """Return the Firestore client. Requires Firebase Admin SDK to be initialized first."""
    return firebase_firestore.client()


# ── User ──────────────────────────────────────────────────────────────────────

def ensure_user_exists(db, uid: str, email: str) -> None:
    """Create a user document if it doesn't already exist."""
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        ref.set({"email": email, "created_at": datetime.now(timezone.utc)})


# ── Projects ──────────────────────────────────────────────────────────────────

def _project_ref(db, uid: str, project_id: str):
    return db.collection("users").document(uid).collection("projects").document(project_id)


def create_project(db, uid: str, project_id: str, name: str) -> None:
    _project_ref(db, uid, project_id).set({
        "name": name,
        "namespace": project_id,
        "created_at": datetime.now(timezone.utc),
    })


def get_project(db, uid: str, project_id: str) -> dict | None:
    doc = _project_ref(db, uid, project_id).get()
    return doc.to_dict() if doc.exists else None


def list_projects(db, uid: str) -> list[dict]:
    docs = db.collection("users").document(uid).collection("projects").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_project(db, uid: str, project_id: str) -> None:
    """Delete all document subcollection entries, then the project document."""
    docs_ref = _project_ref(db, uid, project_id).collection("documents")
    for doc in docs_ref.stream():
        doc.reference.delete()
    _project_ref(db, uid, project_id).delete()


# ── Documents ─────────────────────────────────────────────────────────────────

def _document_ref(db, uid: str, project_id: str, document_id: str):
    return _project_ref(db, uid, project_id).collection("documents").document(document_id)


def create_document_meta(db, uid: str, project_id: str, document_id: str, filename: str, chunks_indexed: int) -> None:
    _document_ref(db, uid, project_id, document_id).set({
        "filename": filename,
        "chunks_indexed": chunks_indexed,
        "created_at": datetime.now(timezone.utc),
    })


def get_document_meta(db, uid: str, project_id: str, document_id: str) -> dict | None:
    doc = _document_ref(db, uid, project_id, document_id).get()
    return doc.to_dict() if doc.exists else None


def list_documents(db, uid: str, project_id: str) -> list[dict]:
    docs = _project_ref(db, uid, project_id).collection("documents").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def delete_document_meta(db, uid: str, project_id: str, document_id: str) -> None:
    _document_ref(db, uid, project_id, document_id).delete()
