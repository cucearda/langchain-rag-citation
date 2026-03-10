# Project Restructure Design

**Date:** 2026-03-10

## Problem

The project has an inconsistent flat structure: domain modules (`agents.py`, `document_loading.py`) and infrastructure modules (`auth.py`, `firestore.py`, `vector_store.py`) all live at the root alongside `main.py`, while only the routers are grouped into a folder.

## Proposed Structure

```
infra/
  __init__.py
  auth.py             # Firebase Auth verification
  firestore.py        # Firestore client and helpers
  vector_store.py     # Pinecone vector store

routers/              # unchanged
  __init__.py
  citations.py
  documents.py
  projects.py

services/
  __init__.py
  agents.py           # LangChain retriever + citator agents
  document_loading.py # GROBID parsing + chunking

main.py               # unchanged
models.py             # unchanged (flat for now)
```

## Layer Responsibilities

- **`infra/`** — External service clients and cross-cutting infrastructure (Firebase Auth, Firestore, Pinecone). No business logic.
- **`services/`** — Domain logic: RAG pipeline, document ingestion. Called by routers.
- **`routers/`** — FastAPI route handlers. Thin layer that delegates to services and infra.
- **Root** — App entrypoint (`main.py`) and shared Pydantic models (`models.py`).

## Changes Required

1. Create `infra/` and `services/` packages with `__init__.py` files.
2. Move files: `auth.py`, `firestore.py`, `vector_store.py` → `infra/`; `agents.py`, `document_loading.py` → `services/`.
3. Update all import paths in `main.py` and all routers.
4. Delete moved files from root.
5. Update `CLAUDE.md` to reflect new structure.
