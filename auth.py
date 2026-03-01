# auth.py
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
        cred = firebase_admin.credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"))
        firebase_admin.initialize_app(cred)
        _initialized = True


async def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    token = authorization.removeprefix("Bearer ")
    try:
        _ensure_firebase()
        return fa_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=e["default_message"])
