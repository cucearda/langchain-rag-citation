# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth import _ensure_firebase
from routers import citations, documents, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_firebase()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(citations.router)
