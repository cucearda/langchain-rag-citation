# auth.py
import json
import os

import firebase_admin
from firebase_admin import auth as fa_auth
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

_initialized = False


def _ensure_firebase():
    global _initialized
    if not _initialized:
        # Production: set FIREBASE_SERVICE_ACCOUNT_JSON to the full contents of the service account JSON
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        # Local: set FIREBASE_SERVICE_ACCOUNT_PATH to the path of the service account JSON file
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if sa_json:
            cred = firebase_admin.credentials.Certificate(json.loads(sa_json))
        elif sa_path:
            cred = firebase_admin.credentials.Certificate(sa_path)
        else:
            raise RuntimeError("No Firebase credentials provided")
        firebase_admin.initialize_app(cred)
        _initialized = True


async def get_current_user(authorization: str | None = Header(None)) -> dict:
    if os.getenv("DISABLE_AUTH") == "true":
        return {"uid": "test-user", "email": "test@example.com"}
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    token = authorization.removeprefix("Bearer ")
    try:
        _ensure_firebase()
        return fa_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=e["default_message"])
