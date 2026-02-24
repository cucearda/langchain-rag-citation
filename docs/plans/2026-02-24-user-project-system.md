# User & Project System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Firebase Auth + Firestore-backed user/project multi-tenancy, with per-project Pinecone namespaces for vector isolation.

**Architecture:** The frontend authenticates via Firebase client SDK and sends ID tokens as Bearer tokens. A FastAPI dependency validates each token with the Firebase Admin SDK. Project metadata lives in Firestore; Pinecone namespaces (named by project UUID) isolate each project's vectors.

**Tech Stack:** FastAPI, Firebase Admin SDK (`firebase-admin`), Firestore (via `firebase_admin.firestore`), Pinecone, LangChain, VoyageAI, Anthropic.

---

## Prerequisites / Env Setup

Before starting, you need a Firebase project:
1. Go to [Firebase Console](https://console.firebase.google.com) → Create project
2. Enable **Authentication** (Email/Password or Google — handled by frontend)
3. Enable **Firestore Database** (start in test mode for dev)
4. Go to Project Settings → Service Accounts → Generate new private key → download JSON
5. Add to `.env`:
   ```
   FIREBASE_SERVICE_ACCOUNT_PATH=/absolute/path/to/serviceAccount.json
   ```

---

## Task 1: Install Dependencies

**Files:**
- Modify: `requirements.txt` (or equivalent)

**Step 1: Install firebase-admin**

```bash
pip install firebase-admin
```

`firebase-admin` bundles both Firebase Auth and Firestore client — no separate `google-cloud-firestore` install needed.

**Step 2: Verify install**

```bash
python -c "import firebase_admin; print('ok')"
```

Expected: `ok`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add firebase-admin dependency"
```

---

## Task 2: Create `auth.py` — Firebase token validation

**Files:**
- Create: `auth.py`
- Create: `tests/test_auth.py`

**Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_auth.py`:

```python
# tests/test_auth.py
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends


def make_app():
    from auth import get_current_user
    app = FastAPI()

    @app.get("/me")
    async def me(user: dict = Depends(get_current_user)):
        return {"uid": user["uid"]}

    return app


def test_valid_token_returns_uid():
    with patch("auth.firebase_admin") as mock_fb, \
         patch("auth.fa_auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {"uid": "user-123", "email": "a@b.com"}
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer valid-token"})
    assert resp.status_code == 200
    assert resp.json()["uid"] == "user-123"


def test_missing_header_returns_401():
    with patch("auth.firebase_admin"), patch("auth.fa_auth"):
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me")
    assert resp.status_code == 422  # FastAPI missing header = 422


def test_invalid_token_returns_401():
    with patch("auth.firebase_admin"), \
         patch("auth.fa_auth") as mock_auth:
        mock_auth.verify_id_token.side_effect = Exception("invalid token")
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401


def test_malformed_header_returns_401():
    with patch("auth.firebase_admin"), patch("auth.fa_auth"):
        app = make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/me", headers={"Authorization": "NotBearer token"})
    assert resp.status_code == 401
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth'`

**Step 3: Create `auth.py`**

```python
# auth.py
import os

import firebase_admin
from firebase_admin import auth as fa_auth, credentials
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

_initialized = False


def _ensure_firebase():
    global _initialized
    if not _initialized:
        cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"))
        firebase_admin.initialize_app(cred)
        _initialized = True


async def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    token = authorization.removeprefix("Bearer ")
    try:
        _ensure_firebase()
        return fa_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

**Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: all 4 tests PASS

**Step 5: Commit**

```bash
git add auth.py tests/__init__.py tests/test_auth.py
git commit -m "feat: add Firebase Auth token validation dependency"
```

---

## Task 3: Create `firestore.py` — Firestore CRUD helpers

**Files:**
- Create: `firestore.py`
- Create: `tests/test_firestore.py`

**Step 1: Write the failing tests**

```python
# tests/test_firestore.py
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest


def make_mock_doc(exists: bool, data: dict = None, doc_id: str = "doc-1"):
    doc = MagicMock()
    doc.exists = exists
    doc.id = doc_id
    doc.to_dict.return_value = data or {}
    return doc


def test_get_project_returns_none_when_missing():
    from firestore import get_project
    db = MagicMock()
    db.collection().document().collection().document().get.return_value = make_mock_doc(exists=False)
    result = get_project(db, "uid-1", "proj-1")
    assert result is None


def test_get_project_returns_data_when_exists():
    from firestore import get_project
    db = MagicMock()
    data = {"name": "My Project", "namespace": "proj-1"}
    db.collection().document().collection().document().get.return_value = make_mock_doc(exists=True, data=data)
    result = get_project(db, "uid-1", "proj-1")
    assert result["name"] == "My Project"


def test_list_projects_returns_list():
    from firestore import list_projects
    db = MagicMock()
    docs = [make_mock_doc(True, {"name": "P1"}, "id-1"), make_mock_doc(True, {"name": "P2"}, "id-2")]
    db.collection().document().collection().stream.return_value = iter(docs)
    result = list_projects(db, "uid-1")
    assert len(result) == 2
    assert result[0]["id"] == "id-1"
    assert result[0]["name"] == "P1"


def test_get_document_meta_returns_none_when_missing():
    from firestore import get_document_meta
    db = MagicMock()
    db.collection().document().collection().document().collection().document().get.return_value = make_mock_doc(exists=False)
    result = get_document_meta(db, "uid-1", "proj-1", "doc-1")
    assert result is None


def test_list_documents_returns_list():
    from firestore import list_documents
    db = MagicMock()
    docs = [make_mock_doc(True, {"filename": "paper.pdf", "chunks_indexed": 5}, "doc-1")]
    db.collection().document().collection().document().collection().stream.return_value = iter(docs)
    result = list_documents(db, "uid-1", "proj-1")
    assert len(result) == 1
    assert result[0]["filename"] == "paper.pdf"
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_firestore.py -v
```

Expected: `ModuleNotFoundError: No module named 'firestore'`

**Step 3: Create `firestore.py`**

```python
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
```

**Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_firestore.py -v
```

Expected: all 5 tests PASS

**Step 5: Commit**

```bash
git add firestore.py tests/test_firestore.py
git commit -m "feat: add Firestore CRUD helpers for users, projects, documents"
```

---

## Task 4: Update `models.py` — New Pydantic models

**Files:**
- Modify: `models.py`

No new tests needed — these are simple data classes exercised by endpoint tests in Task 7.

**Step 1: Add new models to `models.py`**

Append to the bottom of the existing file:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str


class Project(BaseModel):
    id: str
    name: str
    namespace: str
    created_at: datetime


class DocumentMeta(BaseModel):
    id: str
    filename: str
    chunks_indexed: int
    created_at: datetime
```

**Step 2: Verify existing models still import cleanly**

```bash
python -c "from models import Chunk, Citation, CitationSource, CitatorResult, ProjectCreate, Project, DocumentMeta; print('ok')"
```

Expected: `ok`

**Step 3: Commit**

```bash
git add models.py
git commit -m "feat: add Project, ProjectCreate, DocumentMeta Pydantic models"
```

---

## Task 5: Update `vector_store.py` — Add namespace parameter

**Files:**
- Modify: `vector_store.py`
- Create: `tests/test_vector_store.py`

**Step 1: Write the failing test**

```python
# tests/test_vector_store.py
from unittest.mock import patch, MagicMock


def test_get_vector_store_passes_namespace():
    with patch("vector_store.Pinecone") as mock_pc_cls, \
         patch("vector_store.VoyageAIEmbeddings"), \
         patch("vector_store.PineconeVectorStore") as mock_vs_cls:
        mock_pc = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pc_cls.return_value = mock_pc

        from vector_store import get_vector_store
        get_vector_store(namespace="my-namespace")

        call_kwargs = mock_vs_cls.call_args.kwargs
        assert call_kwargs["namespace"] == "my-namespace"


def test_get_vector_store_default_namespace_is_empty():
    with patch("vector_store.Pinecone") as mock_pc_cls, \
         patch("vector_store.VoyageAIEmbeddings"), \
         patch("vector_store.PineconeVectorStore") as mock_vs_cls:
        mock_pc = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pc_cls.return_value = mock_pc

        from vector_store import get_vector_store
        get_vector_store()

        call_kwargs = mock_vs_cls.call_args.kwargs
        assert call_kwargs.get("namespace", "") == ""
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_vector_store.py -v
```

Expected: FAIL — `get_vector_store` does not accept `namespace`

**Step 3: Update `vector_store.py`**

Change `get_vector_store` signature and `PineconeVectorStore` instantiation:

```python
def get_vector_store(namespace: str = ""):
    pc = get_pinecone_client()

    if not pc.has_index(INDEX_NAME):
        pc.create_index(
            name=INDEX_NAME,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(INDEX_NAME)
    embeddings = get_embeddings()

    return PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)
```

**Step 4: Run tests**

```bash
pytest tests/test_vector_store.py -v
```

Expected: both tests PASS

**Step 5: Commit**

```bash
git add vector_store.py tests/test_vector_store.py
git commit -m "feat: add namespace parameter to get_vector_store"
```

---

## Task 6: Refactor `agents.py` — Make vector store injectable

**Files:**
- Modify: `agents.py`

Currently `agents.py` calls `get_vector_store()` at module level and the `retrieve_documents_for_claim` tool closes over the result. We need to move this so a vector store is passed in per-request.

**Step 1: Rewrite `agents.py`**

Replace the entire file:

```python
# agents.py
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool

from models import Citation, CitatorResult

retrieve_documents_for_claim_schema = {
    "type": "object",
    "properties": {
        "claim": {"type": "string"},
        "k": {"type": "number"},
    },
    "required": ["claim", "k"],
}

RETRIEVER_SYSTEM_PROMPT = (
    "You are a research assistant. Given a paragraph, dissect the paragraph into claims "
    "and use the retrieve_documents_for_claim tool to find 1 supporting document for EACH claim. "
    "Call the tool once per claim. Return all retrieved documents. "
    "Do not make up any claims, only use the ones that are stated in the paragraph."
)

CITATOR_SYSTEM_PROMPT = """You are a research assistant. Given a paragraph and a set of source documents, identify every claim in the paragraph that is supported by the provided documents.

For each supported claim:
1. Determine the exact character range (start, end) of the claim text within the paragraph (0-indexed, end is exclusive).
2. State why you chose this source for this claim.
3. Copy a verbatim excerpt from the source document that directly supports the claim.
4. Explain how that excerpt supports the claim.

Only produce citations for claims that are clearly supported by the provided documents. Do not invent citations.

You will return a structured list of Citation objects — one per supported claim.
"""

model = ChatAnthropic(
    model="claude-sonnet-4-20250514", temperature=0, max_tokens=1000, timeout=60
)

citator_agent = create_agent(
    model,
    system_prompt=CITATOR_SYSTEM_PROMPT,
    response_format=CitatorResult,
)


def _make_retrieve_tool(vector_store):
    """Create a retrieve_documents_for_claim tool scoped to the given vector store."""

    @tool(
        description="Retrieve top k documents for a given claim from the vector store",
        args_schema=retrieve_documents_for_claim_schema,
        response_format="content_and_artifact",
    )
    def retrieve_documents_for_claim(claim: str, k: int):
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": k, "score_threshold": 0.5},
        )
        response = retriever.invoke(claim)
        for doc in response:
            doc.metadata.pop("bboxes", None)
            doc.metadata["claim"] = claim
        return ("RetrievedDocumentsForClaim", response)

    return retrieve_documents_for_claim


def invoke_retriever(paragraph: str, vector_store) -> list:
    """Invoke the retriever agent with the given project-scoped vector store."""
    retrieve_tool = _make_retrieve_tool(vector_store)
    agent = create_agent(model, [retrieve_tool], system_prompt=RETRIEVER_SYSTEM_PROMPT)
    result = agent.invoke({"messages": [{"role": "user", "content": paragraph}]})
    docs = []
    for msg in result["messages"]:
        if hasattr(msg, "artifact") and msg.artifact:
            docs.extend(msg.artifact)
    return docs


def invoke_citator(documents, paragraph) -> list[Citation]:
    """Invoke the citator agent. Returns a list of Citation objects."""
    document_messages = []
    seen_ids = set()
    for doc in documents:
        if doc.id in seen_ids:
            continue
        seen_ids.add(doc.id)
        document_messages.append({
            "role": "system",
            "content": (
                f"Paper title: {doc.metadata['paper_title']}\n"
                f"Section title: {doc.metadata['section_title']},\n"
                f"Pages: {doc.metadata['pages']}\n"
                f"Authors: {doc.metadata['authors']}\n"
                f"Year: {doc.metadata['year']}\n"
                f"document text: {doc.page_content}\n"
            ),
        })

    result = citator_agent.invoke({"messages": [
        *document_messages,
        {"role": "system", "content": CITATOR_SYSTEM_PROMPT},
        {"role": "user", "content": f"Paragraph: {paragraph}"},
    ]})
    return result["structured_response"].citations


def reconstruct_cited_paragraph(paragraph: str, citations: list[Citation]) -> str:
    """Reconstruct the cited paragraph by inserting APA markers at citation end positions."""
    sorted_citations = sorted(citations, key=lambda c: c.end, reverse=True)
    result = paragraph
    for citation in sorted_citations:
        first_author = citation.source.authors.split(",")[0].strip()
        apa_marker = f" ({first_author}, {citation.source.year})"
        result = result[:citation.end] + apa_marker + result[citation.end:]
    return result
```

**Step 2: Verify import is clean**

```bash
python -c "from agents import invoke_retriever, invoke_citator, reconstruct_cited_paragraph; print('ok')"
```

Expected: `ok` (no LangChain or Anthropic errors at import time — no agents created at module level now)

**Step 3: Commit**

```bash
git add agents.py
git commit -m "refactor: make vector store injectable in agents, remove module-level global"
```

---

## Task 7: Rewrite `main.py` — Project/document/citation routes

**Files:**
- Modify: `main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing endpoint tests**

```python
# tests/test_main.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest


MOCK_USER = {"uid": "user-123", "email": "test@example.com"}


def make_client(app):
    from auth import get_current_user
    from firestore import get_db
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return TestClient(app, raise_server_exceptions=False)


# ── Projects ──────────────────────────────────────────────────────────────────

def test_create_project_returns_201():
    with patch("main.fs.ensure_user_exists"), \
         patch("main.fs.create_project"), \
         patch("main.fs.get_project", return_value={"name": "P1", "namespace": "ns-1", "created_at": "2026-01-01T00:00:00+00:00"}):
        from main import app
        client = make_client(app)
        resp = client.post("/projects", json={"name": "P1"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "P1"


def test_list_projects_returns_200():
    with patch("main.fs.ensure_user_exists"), \
         patch("main.fs.list_projects", return_value=[]):
        from main import app
        client = make_client(app)
        resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_project_not_found_returns_404():
    with patch("main.fs.get_project", return_value=None):
        from main import app
        client = make_client(app)
        resp = client.delete("/projects/bad-id")
    assert resp.status_code == 404


def test_delete_project_success_returns_204():
    with patch("main.fs.get_project", return_value={"namespace": "ns-1"}), \
         patch("main.fs.delete_project"), \
         patch("main.delete_namespace"):
        from main import app
        client = make_client(app)
        resp = client.delete("/projects/proj-1")
    assert resp.status_code == 204


# ── Documents ─────────────────────────────────────────────────────────────────

def test_list_documents_project_not_found_returns_404():
    with patch("main.fs.get_project", return_value=None):
        from main import app
        client = make_client(app)
        resp = client.get("/projects/bad-id/documents")
    assert resp.status_code == 404


def test_delete_document_not_found_returns_404():
    with patch("main.fs.get_project", return_value={"namespace": "ns-1"}), \
         patch("main.fs.get_document_meta", return_value=None):
        from main import app
        client = make_client(app)
        resp = client.delete("/projects/proj-1/documents/doc-1")
    assert resp.status_code == 404


# ── Citations ─────────────────────────────────────────────────────────────────

def test_citations_project_not_found_returns_404():
    with patch("main.fs.get_project", return_value=None):
        from main import app
        client = make_client(app)
        resp = client.post("/projects/bad-id/citations", json={"paragraph": "test"})
    assert resp.status_code == 404
```

**Step 2: Run to confirm failure**

```bash
pytest tests/test_main.py -v
```

Expected: various failures because `main.py` doesn't have the new routes yet.

**Step 3: Rewrite `main.py`**

```python
# main.py
import tempfile
import os
import uuid

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from langchain_core.documents import Document

import firestore as fs
from auth import get_current_user
from document_loading import parse_pdf_with_grobid, split_chunks
from firestore import get_db
from models import ProjectCreate, CitationRequest
from vector_store import get_vector_store
from agents import invoke_retriever, invoke_citator, reconstruct_cited_paragraph
from pinecone import Pinecone

app = FastAPI()


def delete_namespace(namespace: str) -> None:
    """Delete all vectors in a Pinecone namespace."""
    pc = Pinecone()
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME", "langchain-test-index"))
    index.delete(delete_all=True, namespace=namespace)


# ── Projects ──────────────────────────────────────────────────────────────────

@app.post("/projects", status_code=201)
async def create_project(
    body: ProjectCreate,
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
    from vector_store import INDEX_NAME
    index = pc.Index(INDEX_NAME)
    from vector_store import delete_document_chunks
    delete_document_chunks(index, document_id)

    fs.delete_document_meta(db, uid, project_id, document_id)
    return Response(status_code=204)


# ── Citations ─────────────────────────────────────────────────────────────────

class CitationRequest:
    def __init__(self, paragraph: str):
        self.paragraph = paragraph


from pydantic import BaseModel

class CitationRequest(BaseModel):
    paragraph: str


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
```

**Step 4: Run tests**

```bash
pytest tests/test_main.py -v
```

Expected: all 7 tests PASS

**Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests PASS

**Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add user/project/document routes with Firebase Auth and Firestore"
```

---

## Task 8: Smoke test the running server

**Step 1: Start GROBID**

```bash
docker compose up -d
```

**Step 2: Start the API**

```bash
uvicorn main:app --reload
```

**Step 3: Verify health**

```bash
curl http://localhost:8000/docs
```

Expected: FastAPI docs page loads with all new routes visible.

**Step 4: Get a Firebase test token**

From your Firebase project console or a test script, get a valid ID token. Then:

```bash
TOKEN="your-firebase-id-token"

# Create a project
curl -X POST http://localhost:8000/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Project"}'

# List projects
curl http://localhost:8000/projects \
  -H "Authorization: Bearer $TOKEN"
```

Expected: project returned with `id`, `name`, `namespace`, `created_at`.

**Step 5: Commit any fixes found during smoke test**

```bash
git add -p
git commit -m "fix: address smoke test issues"
```

---

## Summary of File Changes

| File | Action |
|------|--------|
| `auth.py` | Created — Firebase token validation dependency |
| `firestore.py` | Created — Firestore CRUD helpers |
| `models.py` | Modified — added `ProjectCreate`, `Project`, `DocumentMeta` |
| `vector_store.py` | Modified — `get_vector_store` accepts `namespace` param |
| `agents.py` | Modified — vector store injectable, no module-level global |
| `main.py` | Rewritten — project/document/citation routes |
| `tests/test_auth.py` | Created |
| `tests/test_firestore.py` | Created |
| `tests/test_vector_store.py` | Created |
| `tests/test_main.py` | Created |
