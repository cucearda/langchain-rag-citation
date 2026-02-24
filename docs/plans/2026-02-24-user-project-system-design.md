# User & Project System Design

**Date:** 2026-02-24
**Status:** Approved

## Overview

Add multi-tenancy to the RAG citation API. Users authenticate via Firebase Auth, own projects, and each project has its own isolated Pinecone namespace. Documents are uploaded per-project and citations are retrieved scoped to that project's vector store.

## Stack Decisions

- **Auth:** Firebase Auth — frontend authenticates via Firebase client SDK, sends ID token as `Authorization: Bearer <token>`. Server validates with Firebase Admin SDK. No auth endpoints in this repo.
- **Metadata storage:** Firestore — schemaless, no server to manage, natural fit for the user/project/document hierarchy.
- **Vector isolation:** Pinecone namespaces — one index, each project gets its own namespace (= `project_id` UUID).

## Firestore Schema

```
users/{uid}/
  email: string
  created_at: timestamp

  projects/{project_id}/
    name: string
    created_at: timestamp
    namespace: string  # same as project_id

    documents/{document_id}/
      filename: string
      created_at: timestamp
      chunks_indexed: int
```

## API Endpoints

All endpoints require `Authorization: Bearer <firebase_id_token>`.

### Projects
```
POST   /projects                        — create project (body: {name})
GET    /projects                        — list user's projects
DELETE /projects/{project_id}           — delete project + namespace + documents
```

### Documents
```
POST   /projects/{project_id}/documents                   — upload PDF
GET    /projects/{project_id}/documents                   — list documents
DELETE /projects/{project_id}/documents/{document_id}     — delete document + chunks
```

### Citations
```
POST   /projects/{project_id}/citations   — get citations (body: {paragraph})
```

## Data Flows

### Register user (first login)
1. Frontend authenticates with Firebase, gets ID token
2. `get_current_user` dependency validates token → extracts `uid`
3. If `users/{uid}` does not exist in Firestore, create it (email, created_at)

### Create project
1. Validate token → `uid`
2. Generate `project_id` (UUID)
3. Write `users/{uid}/projects/{project_id}` to Firestore
4. Return project metadata

### Upload document
1. Validate token → `uid`
2. Verify `users/{uid}/projects/{project_id}` exists → 404 if not
3. Parse PDF with GROBID, split into chunks (existing logic)
4. Generate `document_id` (UUID)
5. Store chunks in Pinecone namespace=`project_id`, metadata includes `document_id`
6. Write `users/{uid}/projects/{project_id}/documents/{document_id}` to Firestore

### Get citations
1. Validate token → `uid`
2. Verify project exists → 404 if not
3. Initialize vector store scoped to `namespace=project_id`
4. Run existing retriever + citator agents
5. Return citations (same response shape as today)

### Delete document
1. Validate token → `uid`
2. Verify project and document exist in Firestore → 404 if not
3. Call `delete_document_chunks(document_id)` filtered to project namespace
4. Delete `users/{uid}/projects/{project_id}/documents/{document_id}` from Firestore

### Delete project
1. Validate token → `uid`
2. Verify project exists → 404 if not
3. Delete all chunks in project's Pinecone namespace
4. Delete all Firestore documents under `users/{uid}/projects/{project_id}/documents`
5. Delete `users/{uid}/projects/{project_id}` from Firestore

## Error Handling

| Condition | Response |
|-----------|----------|
| Invalid/expired Firebase token | 401 Unauthorized |
| Project not found or not owned by user | 404 Not Found |
| Document not found | 404 Not Found |
| GROBID parse failure | 422 Unprocessable Entity |
| Pinecone/Firestore errors | 500 Internal Server Error |

Note: 404 is returned for both "not found" and "not owned" cases to avoid leaking existence of other users' projects.

## File Changes

**New files:**
- `auth.py` — `get_current_user` FastAPI dependency + Firebase Admin SDK initialization
- `firestore.py` — Firestore client + CRUD helpers for users, projects, documents

**Modified files:**
- `main.py` — new project/document/citation routes; old flat endpoints removed
- `vector_store.py` — `get_vector_store` accepts a `namespace` parameter
- `models.py` — new Pydantic models: `Project`, `ProjectCreate`, `DocumentMeta`

## Testing

- Unit test `get_current_user` by mocking `firebase_admin.auth.verify_id_token`
- Integration test each endpoint with mocked Firestore client
- Existing citation logic requires no new tests — unchanged, just namespaced
