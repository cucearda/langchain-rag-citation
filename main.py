# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infra.auth import _ensure_firebase
from routers import citations, documents, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_firebase()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://rag-citation-chakra-production.up.railway.app/"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(citations.router)
