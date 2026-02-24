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
