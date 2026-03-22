# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infra.auth import _ensure_firebase
from routers import citations, documents, projects
from infra.firestore import initialize_db
from infra.vector_store import initialize_vector_store_index, get_embeddings

firebase_client = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_firebase()
    app.state.db = initialize_db()
    app.state.vector_store_index = initialize_vector_store_index()
    app.state.embeddings = get_embeddings()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://rag-citation-chakra-production.up.railway.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(citations.router)
