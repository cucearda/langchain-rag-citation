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
