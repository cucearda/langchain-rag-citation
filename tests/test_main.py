# tests/test_main.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest


MOCK_USER = {"uid": "user-123", "email": "test@example.com"}


def make_client(app):
    from infra.auth import get_current_user
    from infra.firestore import get_db
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
